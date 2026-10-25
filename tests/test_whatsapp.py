import hashlib
import hmac
import json

import pytest

pytest.importorskip("aiortc")
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from yapwrap.whatsapp import whatsapp_app


def make_app(**kwargs):
    return whatsapp_app(
        yapper=object.__new__(__import__("yapwrap").YapWrap),
        whatsapp_token="t", phone_number_id="1", verify_token="v", webhook_path="/", **kwargs,
    )


def test_verify_webhook():
    with TestClient(make_app()) as client:
        ok = client.get("/", params={"hub.mode": "subscribe", "hub.verify_token": "v", "hub.challenge": "42"})
        assert ok.text == "42"
        bad = client.get("/", params={"hub.mode": "subscribe", "hub.verify_token": "x", "hub.challenge": "42"})
        assert bad.status_code == 403


def test_signature_enforced():
    body = json.dumps({"object": "whatsapp_business_account", "entry": []}).encode()
    sig = "sha256=" + hmac.new(b"s", body, hashlib.sha256).hexdigest()
    with TestClient(make_app(app_secret="s")) as client:
        assert client.post("/", content=body).status_code == 403
        assert client.post("/", content=body, headers={"X-Hub-Signature-256": sig}).status_code == 200
