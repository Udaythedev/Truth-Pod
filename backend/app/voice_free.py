"""
Free-tier cloud voice services (STT/TTS) for student/startup use.

This module provides zero-cost alternatives to Google Cloud Speech/TTS:
- STT: Deepgram free tier (200 min/month) or fallback to mock
- TTS: gTTS (Google Translate TTS - unlimited, free, no API key)

Usage:
    Set USE_FREE_VOICE=1 in .env to enable these providers.
    For Deepgram STT, set DEEPGRAM_API_KEY (free tier: https://console.deepgram.com/signup)
"""

import os
import io
import base64
import hashlib
import struct
import logging
import tempfile
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# Try importing free-tier libraries
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    logger.warning("gTTS not installed. Install with: pip install gTTS")

try:
    from deepgram import DeepgramClient, PrerecordedOptions, FileSource
    DEEPGRAM_AVAILABLE = True
except ImportError:
    DEEPGRAM_AVAILABLE = False
    logger.warning("Deepgram SDK not installed. Install with: pip install deepgram-sdk")


def _generate_silence_wav(duration_s: float = 0.12, rate: int = 8000) -> bytes:
    """Generate a minimal silence WAV for fallback."""
    n_samples = int(duration_s * rate)
    byte_rate = rate * 2
    block_align = 2
    data_size = n_samples * 2
    header = b"RIFF" + struct.pack("<I", 36 + data_size) + b"WAVE"
    fmt = b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, byte_rate, block_align, 16)
    data = b"data" + struct.pack("<I", data_size) + (b"\x00\x00" * n_samples)
    return header + fmt + data


def transcribe_from_bytes_free(data: bytes, mime: Optional[str] = None, timeout: float = 10.0) -> str:
    """
    Transcribe audio using Deepgram free tier (200 min/month).
    
    Requires DEEPGRAM_API_KEY in .env.
    Get free API key at: https://console.deepgram.com/signup
    
    Falls back to deterministic mock if API key not set or error occurs.
    """
    api_key = os.getenv("DEEPGRAM_API_KEY", "").strip()
    
    if DEEPGRAM_AVAILABLE and api_key:
        try:
            deepgram = DeepgramClient(api_key)
            
            # Prepare audio source
            payload: FileSource = {
                "buffer": data,
            }
            
            # Configure options
            options = PrerecordedOptions(
                model="nova-2",  # Latest model
                language=os.getenv("STT_LANGUAGE_CODE", "en-US"),
                smart_format=True,
            )
            
            # Transcribe
            response = deepgram.listen.prerecorded.v("1").transcribe_file(payload, options, timeout=timeout)
            
            # Extract transcript
            transcript = response.results.channels[0].alternatives[0].transcript
            return transcript if transcript else "mock transcription (empty result)"
            
        except Exception as e:
            logger.warning(f"Deepgram STT failed: {e}; using fallback")
    
    # Fallback: deterministic mock based on audio hash
    digest = hashlib.sha256(data).hexdigest()[:8]
    return f"mock transcription {digest}"


def synthesize_text_free(text: str, voice_name: Optional[str] = None) -> Tuple[bytes, str]:
    """
    Synthesize speech using gTTS (Google Translate TTS - completely free, no API key).
    
    gTTS advantages:
    - Zero cost, unlimited usage
    - No API key required
    - Good quality for 50+ languages
    - Perfect for prototypes and student projects
    
    Returns: (audio_bytes, mime_type)
    """
    if not GTTS_AVAILABLE:
        logger.warning("gTTS not available; returning silence placeholder")
        return _generate_silence_wav(), "audio/wav"
    
    try:
        # Get language from env (default English)
        lang = os.getenv("TTS_LANGUAGE_CODE", "en-US")
        # gTTS uses 2-letter codes (en, es, fr, etc.)
        lang_code = lang.split("-")[0] if "-" in lang else lang
        
        # Generate speech
        tts = gTTS(text=text, lang=lang_code, slow=False)
        
        # Save to BytesIO buffer (gTTS outputs MP3)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        audio_bytes = audio_buffer.read()
        
        # Return MP3 format (most IoT devices can handle this; smaller than WAV)
        return audio_bytes, "audio/mpeg"
        
    except Exception as e:
        logger.error(f"gTTS synthesis failed: {e}; returning silence")
        return _generate_silence_wav(), "audio/wav"


# Convenience wrappers matching original voice.py interface
def transcribe_from_bytes(data: bytes, mime: Optional[str] = None, timeout: float = 10.0) -> str:
    """Transcribe audio bytes to text using free-tier provider."""
    return transcribe_from_bytes_free(data, mime, timeout)


def synthesize_text(text: str, voice_name: Optional[str] = None) -> Tuple[bytes, str]:
    """Synthesize text to audio using free-tier provider."""
    return synthesize_text_free(text, voice_name)
