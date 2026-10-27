"""Fully local voice loop: sherpa-onnx STT + Kyutai Pocket TTS, no API keys.
Run: uv run python -m examples.transports.local_offline

Install: pip install "yapwrap[sherpa,kyutai,silero,local]"
Download a streaming Zipformer model from the sherpa-onnx releases, extract it,
and set SHERPA_MODEL_DIR to its folder. Override file names with SHERPA_ENCODER,
SHERPA_DECODER and SHERPA_JOINER if yours differ (e.g. non-int8 files).
Swap EchoAgent for any agent to get a real assistant.
"""

import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path

from yapwrap import AgentEvent, BaseAgent, YapWrap
from yapwrap.stt import SherpaOnnxSTT
from yapwrap.tts import KyutaiTTS
from yapwrap.vad import SileroVAD


class EchoAgent(BaseAgent):
    async def respond(self, text: str) -> AsyncIterator[AgentEvent]:
        yield AgentEvent.text(f"You said: {text}.")


def find(model_dir: Path, env: str, prefix: str) -> str:
    if os.getenv(env):
        return os.environ[env]
    matches = sorted(model_dir.glob(f"{prefix}*.onnx"), key=lambda p: "int8" not in p.name)
    if not matches:
        raise FileNotFoundError(f"No {prefix}*.onnx in {model_dir}; set {env}.")
    return str(matches[0])


async def main():
    model_dir = Path(os.environ["SHERPA_MODEL_DIR"])
    yapper = YapWrap(
        agent=EchoAgent(),
        stt=SherpaOnnxSTT(
            tokens=str(model_dir / "tokens.txt"),
            encoder=find(model_dir, "SHERPA_ENCODER", "encoder"),
            decoder=find(model_dir, "SHERPA_DECODER", "decoder"),
            joiner=find(model_dir, "SHERPA_JOINER", "joiner"),
        ),
        tts=KyutaiTTS(voice=os.getenv("KYUTAI_VOICE", "anna")),
        vad=SileroVAD(),
    )
    await yapper.startlocal()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSession ended.")
