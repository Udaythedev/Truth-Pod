# Device (ESP32) integration notes - TruthPod

This is a short guide and placeholder for the device-side implementation (ESP32 or similar).

High-level responsibilities for the IoT device
- Capture short audio or text input for search/verification.
- Capture an image for face recognition (optional camera module).
- Identify device by MAC or UUID and register with backend to receive a JWT-style device token.
- Send enrollment/recognize requests to backend when required, using the device token in Authorization header.

Connectivity
- Use TLS for all requests to the backend.
- Keep retries and exponential backoff for network failures.

Security
- Store device token securely in non-volatile storage (e.g., ESP32 NVS) and rotate periodically.

Next steps (TODO)
- Provide Arduino/ESP-IDF example that performs device registration and a face enroll request.
- Provide minimal MicroPython example for prototyping on ESP32 boards.
