# WhatsApp voice calls

Let people call your WhatsApp Business number and talk to a YapWrap agent
(Agno + Gemini Flash Lite, Deepgram STT, Cartesia TTS, Silero VAD).

```python
from yapwrap.whatsapp import whatsapp_app

app = whatsapp_app(yapper=build_yapper)   # factory: one YapWrap per call
```

See [server.py](server.py). Pass a `YapWrap` object instead of a factory for a
simple single-call bot; extra simultaneous calls are then rejected.

## How it works

1. A user taps the call button in your business chat.
2. Meta POSTs a `connect` event (with the caller's SDP offer) to your webhook.
3. `whatsapp_app` builds a WebRTC answer, sends `pre_accept` then `accept` to
   the WhatsApp Cloud API, and runs the YapWrap voice session over the call.
4. The call ends on a `terminate` event, a dropped connection, or hang-up.

## 1. Install

From the repository root (PowerShell):

```powershell
uv sync --group examples --extra whatsapp --extra silero --extra deepgram --extra cartesia
```

## 2. Meta setup

1. Create a [Meta developer](https://developers.facebook.com) account and an
   app of type **Business** with the **WhatsApp** product.
2. Under WhatsApp → **API Setup**, note the **Phone number ID** (not the phone
   number) and add your own phone as an allowed recipient for the test number.
3. Get an access token:
   - Quick: **Generate access token** on API Setup. It expires in ~24 hours.
   - Durable: Business Settings → System users → create a user, assign the app
     and WhatsApp account, and generate a token with
     `whatsapp_business_management` and `whatsapp_business_messaging`.
4. Note the **App secret** under App settings → Basic.
5. Choose any string as your **verify token**.

## 3. Enable calling on the number

The console's Calls tab is not always visible, so use the API (replace the
placeholders; works in Postman via Import → Raw text):

```
curl --location --request POST 'https://graph.facebook.com/v23.0/<PHONE_NUMBER_ID>/settings' \
--header 'Authorization: Bearer <ACCESS_TOKEN>' \
--header 'Content-Type: application/json' \
--data '{"calling": {"status": "ENABLED", "call_icon_visibility": "DEFAULT"}}'
```

Check it with `GET .../<PHONE_NUMBER_ID>/settings`. A response of
`{"success": true}` means calling is on. In Postman make sure the body is
**raw → JSON**, otherwise Meta returns
`(#100) One feature setting must be specified`.

## 4. Environment variables

| Variable | Purpose |
| --- | --- |
| `WHATSAPP_ACCESS_TOKEN` | Cloud API token |
| `WHATSAPP_PHONE_NUMBER_ID` | Business phone number ID |
| `WHATSAPP_VERIFY_TOKEN` | Your string; must match the webhook config in Meta |
| `WHATSAPP_APP_SECRET` | Enables `X-Hub-Signature-256` validation (recommended) |
| `WHATSAPP_WEBHOOK_URL` | Public webhook URL; only its path is served (default `/`) |
| `GOOGLE_API_KEY` (or `GEMINI_API_KEY`) | Gemini |
| `DEEPGRAM_API_KEY`, `CARTESIA_API_KEY` | Speech providers |

```powershell
$env:WHATSAPP_ACCESS_TOKEN = "..."
$env:WHATSAPP_PHONE_NUMBER_ID = "..."
$env:WHATSAPP_VERIFY_TOKEN = "choose-a-string"
$env:WHATSAPP_APP_SECRET = "..."
$env:WHATSAPP_WEBHOOK_URL = "https://your-subdomain.ngrok-free.app/whatsapp/webhook"
$env:GOOGLE_API_KEY = "..."; $env:DEEPGRAM_API_KEY = "..."; $env:CARTESIA_API_KEY = "..."
```

The server reads these once at startup. Restart it after changing any of them.

## 5. Expose the server and run

```powershell
ngrok http 8000
uv run python -m examples.whatsapp.server
```

Use the ngrok HTTPS URL plus your path (for example `/whatsapp/webhook`) as
`WHATSAPP_WEBHOOK_URL`. Health check: `GET /health`.

## 6. Register the webhook

In Meta: WhatsApp → **Configuration** → Webhooks.

1. Callback URL: the value of `WHATSAPP_WEBHOOK_URL`; Verify token: your
   `WHATSAPP_VERIFY_TOKEN`. Click **Verify and save** (the server must be
   running).
2. Subscribe to the **calls** field.

## 7. Call it

Open the chat with the business number in WhatsApp and tap the call button.
You should see the `connect` event in the server log, then hear the agent.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| No call button | Calling not enabled (step 3), `call_icon_visibility` is `DISABLE_ALL`, or WhatsApp needs updating/reopening the chat. Calling is not offered everywhere. |
| `Authentication Error` code 190 | Token expired or from another app. Generate a new one, update the env var, **restart** the server. |
| Webhook verification fails | Wrong verify token, wrong path, or server/ngrok not running. |
| 403 `Invalid webhook signature` | `WHATSAPP_APP_SECRET` doesn't match the app that owns the number. |
| Call rings but no event in the log | The `calls` webhook field isn't subscribed, or the callback URL is wrong. |
| `pre_accept failed` | Read the error in the log; usually the token or phone number ID. |
| Connects but silent/no audio | Check provider keys. Behind strict NATs pass `ice_servers=[...]` (STUN/TURN) to `whatsapp_app`. |
| Second caller is rejected | You passed a single `YapWrap`; pass a factory for concurrent calls. |

## Production notes

- Always set `WHATSAPP_APP_SECRET`.
- Use a System User token that does not expire.
- Production numbers require business verification and calling access.
- Configure a TURN server for reliability across networks.
