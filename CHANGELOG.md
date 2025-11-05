# Changelog

All notable changes to this project will be documented here.

## [v0.1.0] - 2025-11-05

Milestone checkpoint: firmware stable, CI/CD set up, and history sanitized.

### Firmware
- ESP32 main board
	- Added self-contained Base64 helpers; fixed prior compile errors
	- Device self-registration; JWT stored via Preferences
	- News headlines fetch; audio playback pipeline
	- Configured API_BASE_URL to https://truth-pod.onrender.com
- ESP32-CAM
	- Stabilized boot (disabled brownout detector), improved camera config
	- Added camera diagnostics and UART gating option
	- Device self-registration + token persistence
	- Face enroll and recognize endpoints wired to backend

### Backend & Integration
- FastAPI backend integrated with device flows (register, trending, TTS/audio, verify)
- Dockerized backend; compose for Postgres + Redis in CI

### CI/CD
- GitHub Actions: tests, buildx Docker image, integration checks
- Publish to GHCR with lowercase owner (prevents invalid tag errors)
- Release workflow on version tags (v*) with auto-generated changelog body

### Security & History
- Removed leaked keys from docs; scrubbed history using replace-text rules
- Added gitleaks-based secret scanning in CI and optional pre-commit hooks

### Docs & Repo Hygiene
- FREE_TIER_SETUP.md sanitized and de-duplicated
- Added quickstart notes for firmware and backend
- Cleaned temporary branches; repository GC

----

[v0.1.0]: https://github.com/Udaythedev/Truth-Pod/releases/tag/v0.1.0
