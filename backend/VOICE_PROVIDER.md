STT/TTS Provider (Google Cloud) — Configuration

This project includes a provider-agnostic helper at `app/voice.py`.

By default the helper uses a deterministic local fallback (a tiny silence WAV for TTS and a hash-based mock transcription).

To enable Google Cloud Speech-to-Text and Text-to-Speech, set these environment variables in your deployment or CI:

- `GOOGLE_CLOUD_PROJECT` — the GCP project id (presence of this var enables the provider path).
- `GOOGLE_APPLICATION_CREDENTIALS` — path to the service account JSON key file (standard Google SDK env var).
- Optional: `STT_LANGUAGE_CODE` (default: `en-US`), `TTS_LANGUAGE_CODE` (default: `en-US`).
- Optional reliability knobs: `VOICE_RETRIES` (default: `1`) and `VOICE_RETRY_DELAY` seconds (default: `0.0`). These control simple retry/backoff around provider calls.

Notes for CI:
- Never commit service account keys to the repo. Use CI secrets and set `GOOGLE_APPLICATION_CREDENTIALS` to a file path created at runtime from the secret content.
- Tests in `backend/tests/test_voice.py` mock the Google client classes — they do not require real credentials.

If you'd like another provider (e.g., OpenAI/Whisper, AssemblyAI), we can add a provider adapter and select by ENV.
