import os
import base64
import hashlib
import struct
from typing import Tuple, Optional
import logging
import time

try:
    from google.cloud import speech_v1 as speech
    from google.cloud import texttospeech_v1 as tts
    GOOGLE_LIBS_AVAILABLE = True
except Exception:
    speech = None
    tts = None
    GOOGLE_LIBS_AVAILABLE = False


    logger = logging.getLogger(__name__)


def _generate_silence_wav(duration_s: float = 0.12, rate: int = 8000) -> bytes:
    n_samples = int(duration_s * rate)
    byte_rate = rate * 2
    block_align = 2
    data_size = n_samples * 2
    header = b"RIFF" + struct.pack("<I", 36 + data_size) + b"WAVE"
    fmt = b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, byte_rate, block_align, 16)
    data = b"data" + struct.pack("<I", data_size) + (b"\x00\x00" * n_samples)
    return header + fmt + data


def _pcm16_to_wav(pcm_bytes: bytes, sample_rate: int = 24000) -> bytes:
    """Wrap raw PCM16 (LINEAR16) bytes into a WAV container."""
    n_samples = len(pcm_bytes) // 2
    byte_rate = sample_rate * 2
    block_align = 2
    data_size = len(pcm_bytes)
    header = b"RIFF" + struct.pack("<I", 36 + data_size) + b"WAVE"
    fmt = b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, byte_rate, block_align, 16)
    data = b"data" + struct.pack("<I", data_size) + pcm_bytes
    return header + fmt + data


def transcribe_from_bytes(data: bytes, mime: Optional[str] = None, timeout: float = 10.0) -> str:
    """Transcribe raw audio bytes to text.

    Uses Google Cloud Speech when available and configured via `GOOGLE_CLOUD_PROJECT` and
    (optionally) `GOOGLE_APPLICATION_CREDENTIALS`. Otherwise returns a deterministic mock.
    """
    if GOOGLE_LIBS_AVAILABLE and os.getenv("GOOGLE_CLOUD_PROJECT"):
        # Simple retry with backoff to improve resilience against transient errors
        max_retries = int(os.getenv("VOICE_RETRIES", "1"))
        delay_s = float(os.getenv("VOICE_RETRY_DELAY", "0.0"))
        last_err: Optional[Exception] = None
        for attempt in range(1, max_retries + 1):
            try:
                client = speech.SpeechClient()
                audio = speech.RecognitionAudio(content=data)
                # Best-effort: let the API auto-detect encoding unless it's obviously LINEAR16
                encoding = speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED
                if mime and ("wav" in mime or "x-wav" in mime or "wave" in mime):
                    encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16
                config = speech.RecognitionConfig(
                    encoding=encoding,
                    sample_rate_hertz=int(os.getenv("STT_SAMPLE_RATE", "16000")),
                    language_code=os.getenv("STT_LANGUAGE_CODE", "en-US"),
                )
                response = client.recognize(config=config, audio=audio, timeout=timeout)
                texts = [r.alternatives[0].transcript for r in response.results if r.alternatives]
                return " ".join(texts)
            except Exception as e:
                last_err = e
                logger.debug("STT provider error on attempt %d/%d: %s", attempt, max_retries, e)
                if attempt < max_retries and delay_s > 0:
                    time.sleep(delay_s)
        # fall through to deterministic mock on any provider error after retries
        logger.warning("STT provider failed after %d attempt(s): %s; using fallback.", max_retries, last_err)

    digest = hashlib.sha256(data).hexdigest()[:8]
    return f"mock transcription {digest}"


def synthesize_text(text: str, voice_name: Optional[str] = None) -> Tuple[bytes, str]:
    """Synthesize text to audio bytes and return (audio_bytes, mime_type).

    Uses Google Cloud TTS when available and configured; otherwise returns a tiny silence WAV placeholder.
    When using Google TTS we request LINEAR16 and wrap the result into a WAV container for broad compatibility.
    """
    if GOOGLE_LIBS_AVAILABLE and os.getenv("GOOGLE_CLOUD_PROJECT"):
        max_retries = int(os.getenv("VOICE_RETRIES", "1"))
        delay_s = float(os.getenv("VOICE_RETRY_DELAY", "0.0"))
        last_err: Optional[Exception] = None
        for attempt in range(1, max_retries + 1):
            try:
                client = tts.TextToSpeechClient()
                input_text = tts.SynthesisInput(text=text)
                # select voice parameters
                language_code = os.getenv("TTS_LANGUAGE_CODE", "en-US")
                ssml_gender = os.getenv("TTS_GENDER", "NEUTRAL")
                voice_params = tts.VoiceSelectionParams(language_code=language_code)
                audio_sample_rate = int(os.getenv("TTS_SAMPLE_RATE", "24000"))
                audio_config = tts.AudioConfig(audio_encoding=tts.AudioEncoding.LINEAR16, sample_rate_hertz=audio_sample_rate)
                response = client.synthesize_speech(input=input_text, voice=voice_params, audio_config=audio_config)
                # response.audio_content is raw LINEAR16 PCM; wrap into WAV
                wav = _pcm16_to_wav(response.audio_content, sample_rate=audio_sample_rate)
                return wav, "audio/wav"
            except Exception as e:
                last_err = e
                logger.debug("TTS provider error on attempt %d/%d: %s", attempt, max_retries, e)
                if attempt < max_retries and delay_s > 0:
                    time.sleep(delay_s)
        logger.warning("TTS provider failed after %d attempt(s): %s; using fallback.", max_retries, last_err)

    wav = _generate_silence_wav()
    return wav, "audio/wav"
