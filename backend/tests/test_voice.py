import os
import base64
from app import voice


def test_transcribe_fallback():
    # ensure fallback path (no GOOGLE_CLOUD_PROJECT)
    os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
    data = b"hello-audio-bytes"
    text = voice.transcribe_from_bytes(data)
    assert text.startswith("mock transcription")


def test_synthesize_fallback():
    os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
    text = "hello world"
    audio, mime = voice.synthesize_text(text)
    assert isinstance(audio, (bytes, bytearray))
    assert mime == "audio/wav"


def test_provider_path_monkeypatch(monkeypatch):
    # simulate Google libs and a successful response
    os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"

    class FakeRecognitionAlternative:
        def __init__(self, transcript):
            self.transcript = transcript

    class FakeResult:
        def __init__(self, text):
            self.alternatives = [FakeRecognitionAlternative(text)]

    class FakeSpeechClient:
        def recognize(self, config=None, audio=None, timeout=None):
            return type("R", (), {"results": [FakeResult("recognized text")]})()

    class FakeTTSResponse:
        def __init__(self):
            self.audio_content = b"FAKEAUDIO"

    class FakeTTSClient:
        def synthesize_speech(self, input=None, voice=None, audio_config=None):
            return FakeTTSResponse()

    # monkeypatch the imported modules/clients
    monkeypatch.setattr(voice, "GOOGLE_LIBS_AVAILABLE", True)
    # Provide a fake speech module with the attributes used by app.voice
    class FakeRecognitionConfig:
        class AudioEncoding:
            ENCODING_UNSPECIFIED = 0
        def __init__(self, **kw):
            # accept any kwargs used by the real client
            self.encoding = kw.get("encoding")
            self.sample_rate_hertz = kw.get("sample_rate_hertz")
            self.language_code = kw.get("language_code")
    FakeSpeechModule = type("m", (), {
        "SpeechClient": FakeSpeechClient,
        "RecognitionAudio": lambda content=None: None,
        "RecognitionConfig": FakeRecognitionConfig,
    })
    monkeypatch.setattr(voice, "speech", FakeSpeechModule)
    # Provide a fake tts module
    FakeTTSModule = type("m", (), {
        "TextToSpeechClient": FakeTTSClient,
        "SynthesisInput": lambda text=None: None,
        "VoiceSelectionParams": lambda **kw: None,
        "AudioConfig": lambda **kw: None,
        "AudioEncoding": type("e", (), {"LINEAR16": 1}),
    })
    monkeypatch.setattr(voice, "tts", FakeTTSModule)

    # transcribe should call fake client and return recognized text
    text = voice.transcribe_from_bytes(b"audio")
    assert "recognized text" in text

    # synthesize should return fake bytes wrapped into WAV by our implementation
    audio, mime = voice.synthesize_text("hi")
    assert mime == "audio/wav"
    assert b"FAKEAUDIO" in audio
