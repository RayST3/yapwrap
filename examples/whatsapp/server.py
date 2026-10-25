"""WhatsApp Business voice calls with Agno + Gemini Flash Lite.
Run: uv run python -m examples.whatsapp.server
Full setup guide (Meta, ngrok, env vars): examples/whatsapp/README.md.
"""

import os

from agno.agent import Agent
from agno.models.google import Gemini

from yapwrap import YapWrap
from yapwrap.agents import AgnoAgent
from yapwrap.stt import DeepgramSTT
from yapwrap.tts import CartesiaTTS
from yapwrap.vad import SileroVAD
from yapwrap.whatsapp import whatsapp_app


def build_yapper() -> YapWrap:
    agent = Agent(
        model=Gemini(
            id=os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest"),
            api_key=os.getenv("GOOGLE_API_KEY") or os.environ["GEMINI_API_KEY"],
        ),
        instructions="You are a friendly voice assistant. Give natural spoken answers in at most two sentences. Avoid markdown.",
        markdown=False,
    )
    return YapWrap(
        agent=AgnoAgent(agent),
        stt=DeepgramSTT(api_key=os.environ["DEEPGRAM_API_KEY"]),
        tts=CartesiaTTS(api_key=os.environ["CARTESIA_API_KEY"]),
        vad=SileroVAD(),
    )


# A factory gives every call its own YapWrap, so calls can run concurrently.
app = whatsapp_app(yapper=build_yapper)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
