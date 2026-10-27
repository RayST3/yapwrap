"""Speech-to-Text (STT) streaming transcription providers for yapwrap."""

from yapwrap.core.base import BaseSTT
from yapwrap.stt.deepgram import DeepgramSTT
from yapwrap.stt.assemblyai import AssemblyAISTT
from yapwrap.stt.openai_realtime import OpenAIRealtimeSTT
from yapwrap.stt.elevenlabs import ElevenLabsSTT
from yapwrap.stt.speechmatics import SpeechmaticsSTT
from yapwrap.stt.soniox import SonioxSTT
from yapwrap.stt.gladia import GladiaSTT
from yapwrap.stt.google_chirp import GoogleChirpSTT
from yapwrap.stt.sherpa_onnx import SherpaOnnxSTT

__all__ = [
    "SherpaOnnxSTT",
    "BaseSTT",
    "DeepgramSTT",
    "AssemblyAISTT",
    "OpenAIRealtimeSTT",
    "ElevenLabsSTT",
    "SpeechmaticsSTT",
    "SonioxSTT",
    "GladiaSTT",
    "GoogleChirpSTT",
]

