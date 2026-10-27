"""Local streaming STT using sherpa-onnx transducer models (no API key, CPU)."""

import asyncio
from collections.abc import AsyncIterator
from typing import Any, Optional

from yapwrap.core.base import BaseSTT
from yapwrap.core.events import TranscriptEvent


class SherpaOnnxSTT(BaseSTT):
    """Streaming Zipformer/transducer recognition with partial transcripts.

    Download a model from the sherpa-onnx releases and pass its files, e.g. the
    streaming-zipformer-en model's tokens.txt, encoder, decoder and joiner .onnx.
    """

    def __init__(
        self, tokens: str, encoder: str, decoder: str, joiner: str, *,
        sample_rate: int = 16000, num_threads: int = 2, provider: str = "cpu",
        decoding_method: str = "greedy_search", recognizer: Optional[Any] = None,
    ) -> None:
        self.sample_rate = sample_rate
        self._recognizer = recognizer
        self._options = dict(
            tokens=tokens, encoder=encoder, decoder=decoder, joiner=joiner,
            num_threads=num_threads, sample_rate=sample_rate, provider=provider,
            decoding_method=decoding_method,
        )

    def _load(self):
        if self._recognizer is None:
            try:
                import sherpa_onnx
            except ImportError as exc:
                raise ImportError("SherpaOnnxSTT requires `pip install yapwrap[sherpa]`.") from exc
            self._recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(**self._options)
        return self._recognizer

    @staticmethod
    def _text(result: Any) -> str:
        return (result if isinstance(result, str) else getattr(result, "text", "")).strip()

    def _feed(self, stream, pcm: bytes) -> str:
        import numpy as np

        recognizer = self._recognizer
        samples = np.frombuffer(pcm[: len(pcm) // 2 * 2], dtype="<i2").astype(np.float32) / 32768.0
        stream.accept_waveform(self.sample_rate, samples)
        while recognizer.is_ready(stream):
            recognizer.decode_stream(stream)
        return self._text(recognizer.get_result(stream))

    def _finish(self, stream) -> str:
        import numpy as np

        recognizer = self._recognizer
        stream.accept_waveform(self.sample_rate, np.zeros(int(self.sample_rate * 0.4), dtype=np.float32))
        stream.input_finished()
        while recognizer.is_ready(stream):
            recognizer.decode_stream(stream)
        return self._text(recognizer.get_result(stream))

    async def transcribe(self, audio: AsyncIterator[bytes]) -> AsyncIterator[str | TranscriptEvent]:
        recognizer = await asyncio.to_thread(self._load)
        stream = recognizer.create_stream()
        last = ""
        async for chunk in audio:
            if not chunk:
                continue
            text = await asyncio.to_thread(self._feed, stream, chunk)
            if text and text != last:
                last = text
                yield TranscriptEvent(text, is_final=False)
        final = await asyncio.to_thread(self._finish, stream)
        if final or last:
            yield TranscriptEvent(final or last, is_final=True)
