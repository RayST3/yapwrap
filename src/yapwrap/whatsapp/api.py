"""Minimal WhatsApp Cloud API calling client."""

from typing import Any

import httpx

GRAPH_URL = "https://graph.facebook.com/v23.0/"


class WhatsAppCallsAPI:
    """Answer, reject, and terminate WhatsApp voice calls."""

    def __init__(self, token: str, phone_number_id: str, client: httpx.AsyncClient) -> None:
        self._token = token
        self._url = f"{GRAPH_URL}{phone_number_id}/calls"
        self._client = client

    async def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._client.post(
            self._url,
            headers={"Authorization": f"Bearer {self._token}"},
            json={"messaging_product": "whatsapp", **payload},
        )
        try:
            return response.json()
        except ValueError:
            return {"success": False, "error": response.text}

    async def answer(self, call_id: str, action: str, sdp: str, caller: str) -> dict[str, Any]:
        """Send ``pre_accept`` or ``accept`` with the SDP answer."""
        return await self._post({
            "to": caller,
            "action": action,
            "call_id": call_id,
            "session": {"sdp": sdp, "sdp_type": "answer"},
        })

    async def reject(self, call_id: str) -> dict[str, Any]:
        return await self._post({"action": "reject", "call_id": call_id})

    async def terminate(self, call_id: str) -> dict[str, Any]:
        return await self._post({"action": "terminate", "call_id": call_id})
