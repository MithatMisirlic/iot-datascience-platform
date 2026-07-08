# Raspberry Pi Setup

The WebSocket client lives in `pi-client/` and has its own `requirements.txt` and
`.env.example`. See `pi-client/README.md` for complete configuration and mock-mode
instructions.

Before hardware mode:

1. Enable Linux I2C and verify the MPU6050 address, normally `0x68`.
2. Install PortAudio for the INMP441/sounddevice input path.
3. Verify the camera is exposed through the configured OpenCV device index.
4. Confirm `ws://192.168.0.182:8080/stream` is reachable from the Pi.
5. Start with `PI_MOCK_MODE=true`, then enable hardware sources individually.

The client never connects to the backend database. Hardware access is isolated in
`pi_client/recorders/` and may be replaced with mocks on non-Pi systems.
