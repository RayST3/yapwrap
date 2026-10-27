"""Local streaming TTS using Kyutai Pocket TTS (no API key, CPU)."""

import asyncio
from collections.abc import AsyncIterator
from typing import Any, Optional

from yapwrap.core.audio import PCM16Stream
from yapwrap.core.base import BaseTTS

_DONE = object()


class KyutaiTTS(BaseTTS):
    """Stream Pocket TTS audio, resampled to the session rate (model emits ~24 kHz)."""

    def __init__(
        self, voice: str = "alba", sample_rate: int = 16000, *, model: Optional[Any] = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.voice = voice
        self._model = model
        self._voice_state: Any = None

    def _load(self) -> None:
        if self._model is None:
            try:
                from pocket_tts import TTSModel
            except ImportError as exc:
                raise ImportError("KyutaiTTS requires `pip install yapwrap[kyutai]`.") from exc
            self._model = TTSModel.load_model()
        if self._voice_state is None:
            self._voice_state = self._model.get_state_for_audio_prompt(self.voice)

    @staticmethod
    def _to_pcm16(chunk: Any) -> bytes:
        import numpy as np

        array = chunk.detach().cpu().numpy() if hasattr(chunk, "detach") else np.asarray(chunk)
        samples = np.clip(array.astype(np.float32).reshape(-1), -1.0, 1.0)
        return (samples * 32767.0).astype("<i2").tobytes()

    async def synthesize(self, text: str) -> AsyncIterator[bytes]:
        if not text.strip():
            return
        await asyncio.to_thread(self._load)
        source_rate = int(getattr(self._model, "sample_rate", 24000))
        converter = PCM16Stream(source_rate, self.sample_rate)
        generator = iter(self._model.generate_audio_stream(self._voice_state, text))

        def next_chunk():
            return next(generator, _DONE)

        try:
            while True:
                chunk = await asyncio.to_thread(next_chunk)
                if chunk is _DONE:
                    break
                pcm = converter.process(self._to_pcm16(chunk))
                if pcm:
                    yield pcm
        finally:
            close = getattr(generator, "close", None)
            if close is not None:
                close()
        tail = converter.finish()
        if tail:
            yield tail
