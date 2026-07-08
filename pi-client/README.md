# Raspberry Pi WebSocket Client

Independent asyncio client for streaming sensor frames to
`ws://192.168.0.182:8080/stream`. It has no backend database dependency.

## Streams

- Raw MPU6050 accelerometer and gyroscope frames at approximately 60 Hz.
- INMP441/PortAudio RMS amplitude frames at approximately 60 Hz.
- Optional base64 JPEG camera frames at configurable FPS.
- Local WAV capture controlled by `start_wav` and `stop_wav` server commands.

All outbound WebSocket messages are JSON objects matching the specified `imu`,
`audio`, and `camera` frame structures. One sender task serializes frames from all
enabled producers. The client reconnects with exponential backoff capped by the
configured maximum.

## Raspberry Pi Setup

From the repository root:

```bash
cd pi-client
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Enable I2C for the MPU6050. `sounddevice` also requires PortAudio to be installed
by the operating system. The camera adapter uses an OpenCV-compatible camera
device index; camera streaming is disabled by default.

Export configuration variables or source a reviewed environment file:

```bash
cp .env.example .env
set -a
source .env
set +a
python -m pi_client.main
```

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `PI_WS_HOST` | `192.168.0.182` | WebSocket server host. |
| `PI_WS_PORT` | `8080` | WebSocket server port. |
| `PI_WS_PATH` | `/stream` | WebSocket path. |
| `PI_IMU_ENABLED` | `true` | Enable MPU6050 frames. |
| `PI_AUDIO_ENABLED` | `true` | Enable RMS audio frames and WAV commands. |
| `PI_CAMERA_ENABLED` | `false` | Enable JPEG frames. |
| `PI_MOCK_MODE` | `false` | Use deterministic hardware-free recorders. |
| `PI_IMU_RATE_HZ` | `60` | IMU target frame rate. |
| `PI_AUDIO_RATE_HZ` | `60` | Audio RMS target frame rate. |
| `PI_CAMERA_FPS` | `5` | Camera target frame rate. |
| `PI_RECONNECT_INITIAL_SECONDS` | `1` | Initial reconnect delay. |
| `PI_RECONNECT_MAX_SECONDS` | `30` | Maximum reconnect delay. |
| `PI_I2C_BUS` | `1` | Linux I2C bus number. |
| `PI_MPU6050_ADDRESS` | `0x68` | MPU6050 I2C address. |
| `PI_AUDIO_SAMPLE_RATE` | `48000` | Audio sample rate. |
| `PI_CAMERA_INDEX` | `0` | OpenCV camera device index. |
| `PI_CAMERA_JPEG_QUALITY` | `80` | JPEG quality from 1 to 100. |
| `PI_WAV_DIR` | `./recordings` | Directory for commanded WAV files. |

## Hardware-Free Test

Mock mode requires only `websockets` and the Python standard library at runtime:

```bash
cd pi-client
PI_MOCK_MODE=true PI_CAMERA_ENABLED=true python -m pi_client.main
```

On Windows PowerShell:

```powershell
cd pi-client
$env:PI_MOCK_MODE="true"
$env:PI_CAMERA_ENABLED="true"
python -m pi_client.main
```

The configured WebSocket server must still be reachable. Mock mode generates
deterministic IMU/audio frames and a static JPEG; it never opens hardware.
