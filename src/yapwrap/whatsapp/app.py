"""FastAPI webhook app bridging WhatsApp Cloud API calls to YapWrap over WebRTC."""

import asyncio
import hashlib
import hmac
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Callable, Optional, Union
from urllib.parse import urlparse

from yapwrap.core.yapwrap import YapWrap
from yapwrap.whatsapp.api import WhatsAppCallsAPI

logger = logging.getLogger("yapwrap.whatsapp")

DEFAULT_STUN = "stun:stun.l.google.com:19302"


def _filter_sdp(sdp: str) -> str:
    """WhatsApp accepts only SHA-256 DTLS fingerprints."""
    lines = [
        line for line in sdp.splitlines()
        if not (line.startswith("a=fingerprint:") and not line.startswith("a=fingerprint:sha-256"))
    ]
    return "\r\n".join(lines) + "\r\n"


def _require(value: Optional[str], env: str, name: str) -> str:
    value = value or os.getenv(env)
    if not value:
        raise ValueError(f"Missing {name}: pass it to whatsapp_app() or set {env}")
    return value


def whatsapp_app(
    yapper: Union[YapWrap, Callable[[], YapWrap]],
    *,
    whatsapp_token: Optional[str] = None,
    phone_number_id: Optional[str] = None,
    verify_token: Optional[str] = None,
    app_secret: Optional[str] = None,
    ice_servers: Optional[list[str]] = None,
    webhook_path: Optional[str] = None,
) -> Any:
    """Build a FastAPI app that answers WhatsApp voice calls.

    ``yapper`` is a YapWrap, which serves one call at a time (further calls are
    rejected), or a zero-argument factory returning a fresh YapWrap per call.
    Unset options fall back to WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_VERIFY_TOKEN, WHATSAPP_APP_SECRET and WHATSAPP_WEBHOOK_URL (only
    its path is served; default "/"). Setting an app secret enables
    X-Hub-Signature-256 validation, which is strongly advised.
    """
    try:
        import httpx
        from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCSessionDescription
        from fastapi import FastAPI, HTTPException, Request
        from fastapi.responses import PlainTextResponse
    except ImportError as exc:
        raise ImportError("whatsapp_app requires pip install 'yapwrap[web,webrtc]'") from exc
    from yapwrap.transports.webrtc import WebRTCTransport

    token = _require(whatsapp_token, "WHATSAPP_ACCESS_TOKEN", "WhatsApp access token")
    phone_id = _require(phone_number_id, "WHATSAPP_PHONE_NUMBER_ID", "phone number ID")
    verify = _require(verify_token, "WHATSAPP_VERIFY_TOKEN", "webhook verify token")
    secret = app_secret or os.getenv("WHATSAPP_APP_SECRET")
    if webhook_path is None:
        webhook_path = urlparse(os.getenv("WHATSAPP_WEBHOOK_URL", "")).path or "/"
    stun = ice_servers if ice_servers is not None else [DEFAULT_STUN]
    factory = yapper if not isinstance(yapper, YapWrap) else (lambda: yapper)

    calls: dict[str, "asyncio.Task[None]"] = {}
    state: dict[str, Any] = {}

    @asynccontextmanager
    async def lifespan(_: Any):
        async with httpx.AsyncClient(timeout=15) as client:
            state["api"] = WhatsAppCallsAPI(token, phone_id, client)
            yield
            running = list(calls.values())
            for task in running:
                task.cancel()
            await asyncio.gather(*running, return_exceptions=True)

    app = FastAPI(title="YapWrap WhatsApp Voice", lifespan=lifespan)

    async def run_call(call: dict[str, Any]) -> None:
        api: WhatsAppCallsAPI = state["api"]
        call_id, caller = call["id"], call["from"]
        wrapper = factory()
        if getattr(wrapper, "_running", False):
            logger.warning("Rejecting call %s: voice session is busy", call_id)
            await api.reject(call_id)
            calls.pop(call_id, None)
            return

        pc = RTCPeerConnection(RTCConfiguration(iceServers=[RTCIceServer(urls=u) for u in stun]))
        transport = WebRTCTransport(pc=pc, sample_rate=wrapper.sample_rate)
        ended = asyncio.Event()

        @pc.on("connectionstatechange")
        def on_state() -> None:
            if pc.connectionState in ("failed", "closed"):
                ended.set()

        voice: Optional["asyncio.Task[None]"] = None
        accepted = False
        try:
            session = call["session"]
            await pc.setRemoteDescription(RTCSessionDescription(sdp=session["sdp"], type="offer"))
            pc.addTrack(transport.create_output_track())
            await pc.setLocalDescription(await pc.createAnswer())
            answer = _filter_sdp(pc.localDescription.sdp)
            for action in ("pre_accept", "accept"):
                result = await api.answer(call_id, action, answer, caller)
                if not result.get("success", False):
                    raise RuntimeError(f"WhatsApp {action} failed: {result}")
            accepted = True
            voice = asyncio.create_task(wrapper.run(transport))
            waiter = asyncio.create_task(ended.wait())
            try:
                await asyncio.wait({voice, waiter}, return_when=asyncio.FIRST_COMPLETED)
            finally:
                waiter.cancel()
            if voice.done():
                await voice
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("WhatsApp call %s failed", call_id)
            if not accepted:
                try:
                    await api.reject(call_id)
                except Exception:
                    logger.exception("Could not reject call %s", call_id)
        finally:
            if voice is not None and not voice.done():
                voice.cancel()
                await asyncio.gather(voice, return_exceptions=True)
            await transport.close()
            await pc.close()
            calls.pop(call_id, None)
            if accepted:
                try:
                    await api.terminate(call_id)
                except Exception:
                    logger.debug("Terminate for call %s failed", call_id, exc_info=True)

    def handle_event(payload: dict[str, Any]) -> None:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") != "calls":
                    continue
                for call in change.get("value", {}).get("calls", []):
                    event, call_id = call.get("event"), call.get("id")
                    if event == "connect" and call_id and call_id not in calls:
                        calls[call_id] = asyncio.create_task(run_call(call))
                    elif event == "terminate" and call_id in calls:
                        calls[call_id].cancel()

    @app.get(webhook_path)
    async def verify_webhook(request: Request):
        params = request.query_params
        if params.get("hub.mode") != "subscribe" or params.get("hub.verify_token") != verify:
            raise HTTPException(status_code=403, detail="Webhook verification failed")
        return PlainTextResponse(params.get("hub.challenge", ""))

    @app.post(webhook_path)
    async def webhook(request: Request):
        body = await request.body()
        if secret:
            expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
            received = request.headers.get("X-Hub-Signature-256", "").removeprefix("sha256=")
            if not hmac.compare_digest(expected, received):
                raise HTTPException(status_code=403, detail="Invalid webhook signature")
        try:
            payload = json.loads(body)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid JSON")
        if payload.get("object") != "whatsapp_business_account":
            raise HTTPException(status_code=400, detail="Unsupported webhook object")
        handle_event(payload)
        return {"status": "ok"}

    @app.get("/health")
    async def health():
        return {"status": "ok", "active_calls": len(calls)}

    return app
