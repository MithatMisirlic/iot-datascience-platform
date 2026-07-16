# Raspberry Pi WebSocket Client

This directory is a self-contained Raspberry Pi deployment unit. It streams sensor frames to the development WebSocket receiver and does not import or access the REST backend, frontend, processing pipeline, or database.

The client can stream:

- MPU6050 IMU frames at approximately 60 Hz.
- INMP441 microphone RMS audio frames at approximately 60 Hz.
- Optional Raspberry Pi camera JPEG frames at configurable FPS.

It connects to:

```text
ws://<PI_WS_HOST>:<PI_WS_PORT><PI_WS_PATH>
```

Default:

```text
ws://192.168.0.182:8080/stream
```

## Current Development Limitation

The development server `tools.dev_ws_server` receives and counts live frames. It does not yet persist those live frames to an exercise-specific `raw_frames.json` file. Backend results are currently created by running `tools.process_exercise` against stored or generated raw frames.

## Deployment Scope

Deploy the contents of this `pi-client` directory directly to the Pi, for example:

```text
/home/pi007/mithat-iot-datascience-platform
```

Do not place the files inside an extra nested `pi-client` directory on the Pi. The remote project root should contain `setup_pi.sh`, `run_pi.sh`, `requirements.txt`, `.env.example`, and `pi_client/` directly.

## Raspberry Pi Prerequisites

Install system packages before running the setup script:

```bash
sudo apt update
sudo apt install -y \
  python3 python3-venv python3-pip python3-dev build-essential \
  i2c-tools alsa-utils libasound2-dev libportaudio2 portaudio19-dev \
  rpicam-apps python3-picamera2
```

On older Raspberry Pi OS releases, `libcamera-apps` may be used instead of `rpicam-apps`.

Enable I2C:

```bash
sudo raspi-config
```

Use **Interface Options > I2C**. INMP441 I2S setup depends on the overlay and wiring used in your hardware build.

Verify camera detection:

```bash
rpicam-hello --list-cameras
```

## First-Time Setup

From the Pi deployment directory:

```bash
cd /home/pi007/mithat-iot-datascience-platform
chmod +x setup_pi.sh
./setup_pi.sh
```

The script:

- Creates `.venv`.
- Installs `requirements.txt`.
- Creates `recordings/`.
- Copies `.env.example` to `.env` if `.env` is missing.
- Makes `run_pi.sh` executable.

Review `.env`, then start the client:

```bash
./run_pi.sh
```

`run_pi.sh` loads `.env`, activates `.venv`, and executes:

```bash
python -m pi_client.main
```

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `PI_WS_HOST` | `192.168.0.182` | Development machine IP or hostname for the WebSocket receiver. |
| `PI_WS_PORT` | `8080` | WebSocket receiver port. |
| `PI_WS_PATH` | `/stream` | WebSocket endpoint path. |
| `PI_IMU_ENABLED` | `true` | Enable MPU6050 IMU frames. |
| `PI_AUDIO_ENABLED` | `true` | Enable audio RMS frames and WAV commands. |
| `PI_CAMERA_ENABLED` | `false` | Enable JPEG camera frames. |
| `PI_MOCK_MODE` | `false` | Use hardware-free mock recorders. |
| `PI_IMU_RATE_HZ` | `60` | IMU frame target rate. |
| `PI_AUDIO_RATE_HZ` | `60` | Audio RMS frame target rate. |
| `PI_CAMERA_FPS` | `5` | Camera frame target rate. |
| `PI_RECONNECT_INITIAL_SECONDS` | `1` | Initial reconnect delay. |
| `PI_RECONNECT_MAX_SECONDS` | `30` | Maximum reconnect delay. |
| `PI_I2C_BUS` | `1` | I2C bus number. |
| `PI_MPU6050_ADDRESS` | `0x68` | MPU6050 I2C address. |
| `PI_AUDIO_SAMPLE_RATE` | `48000` | Audio capture sample rate. |
| `PI_CAMERA_INDEX` | `0` | OpenCV fallback camera index. |
| `PI_CAMERA_JPEG_QUALITY` | `80` | JPEG quality from 1 to 100. |
| `PI_WAV_DIR` | `./recordings` | Local WAV output directory. |

All local paths should be relative to the Pi deployment directory.

## Development Run Order

On the development machine, start the WebSocket receiver:

```bash
python -m tools.dev_ws_server
```

On the Pi, set `PI_WS_HOST` in `.env` to the development machine LAN IP. Then run:

```bash
./run_pi.sh
```

The development receiver should print frame counts once per second:

```text
frames/s imu=60 audio=60 camera=5
```

Counts depend on enabled sensors and hardware performance.

## Testing Without Hardware

Use mock mode to verify networking and protocol framing without connected sensors:

```dotenv
PI_MOCK_MODE=true
PI_IMU_ENABLED=true
PI_AUDIO_ENABLED=true
PI_CAMERA_ENABLED=true
```

Then run:

```bash
./run_pi.sh
```

The mock client still requires a reachable WebSocket receiver.

## Camera-Only Test

Verify the camera first:

```bash
rpicam-hello --list-cameras
```

Then configure `.env`:

```dotenv
PI_IMU_ENABLED=false
PI_AUDIO_ENABLED=false
PI_CAMERA_ENABLED=true
PI_MOCK_MODE=false
PI_CAMERA_FPS=5
PI_CAMERA_JPEG_QUALITY=80
```

Run:

```bash
./run_pi.sh
```

The client uses Picamera2 as the primary CSI camera adapter and captures 320x240 frames. Individual capture or JPEG encoding failures are logged and skipped without closing the WebSocket connection.

## PyCharm Professional Deployment

PyCharm is optional, but it is useful for SFTP deployment and SSH interpreter setup.

### SFTP Deployment

1. Open **Settings > Build, Execution, Deployment > Deployment**.
2. Add an **SFTP** server for the Raspberry Pi.
3. Set the remote root path to `/home/pi007/mithat-iot-datascience-platform`.
4. In **Mappings**, map the local `pi-client` directory to remote `/`.
5. Exclude `.venv`, `.env`, `recordings`, `__pycache__`, and `.idea` from deployment.
6. Upload the directory.

The mapping matters: `setup_pi.sh`, `run_pi.sh`, and `requirements.txt` must be directly in the remote root.

### SSH Interpreter

Run `./setup_pi.sh` once first. Then configure PyCharm to use:

```text
/home/pi007/mithat-iot-datascience-platform/.venv/bin/python
```

Set the remote working directory to:

```text
/home/pi007/mithat-iot-datascience-platform
```

### Remote Execution

Recommended command:

```bash
./run_pi.sh
```

A Python module run configuration can use `pi_client.main`, but then you must provide the `PI_*` environment variables in PyCharm because `.env` is normally loaded by `run_pi.sh`.

## Expected Remote Layout

```text
/home/pi007/mithat-iot-datascience-platform/
|-- .env
|-- .env.example
|-- .gitignore
|-- .venv/
|-- README.md
|-- recordings/
|-- requirements.txt
|-- run_pi.sh
|-- setup_pi.sh
`-- pi_client/
    |-- __init__.py
    |-- main.py
    |-- websocket_client.py
    |-- config/
    |-- recorders/
    |-- storage/
    `-- uploader/
```

## Troubleshooting

### WebSocket Reconnect Loop

Verify the development receiver is running:

```bash
python -m tools.dev_ws_server
```

Check `.env` on the Pi:

```dotenv
PI_WS_HOST=<development-machine-lan-ip>
PI_WS_PORT=8080
PI_WS_PATH=/stream
```

Do not use `PI_WS_HOST=0.0.0.0` on the Pi. Check firewall rules on the development machine.

### Wrong Laptop IP

On Windows, run:

```powershell
ipconfig
```

Use the IPv4 address for the active adapter on the same network as the Pi.

### MPU6050 / I2C Errors

Run:

```bash
i2cdetect -y 1
```

Confirm the sensor appears at the configured `PI_MPU6050_ADDRESS`, usually `0x68`.

### Audio Device Errors

Run:

```bash
arecord -l
```

Verify the INMP441 I2S device appears and that the selected overlay is loaded.

### Camera Not Detected

Run:

```bash
rpicam-hello --list-cameras
```

Check the camera ribbon cable, connector orientation, Pi OS camera stack, and power supply.

### Picamera2 Missing From Venv

Install the system package:

```bash
sudo apt install -y python3-picamera2 rpicam-apps
./setup_pi.sh
```

If needed, keep `PI_CAMERA_ENABLED=false` or use `PI_MOCK_MODE=true` until the Pi camera stack is fixed.

### Stale PyCharm Deployment Files

Delete stale remote files or re-upload the full `pi-client/` directory. Confirm there is not an extra nested `pi-client` directory on the Pi.

### `ModuleNotFoundError`

Run from the Pi deployment root:

```bash
./run_pi.sh
```

If it still fails, rerun:

```bash
./setup_pi.sh
```

Then verify `.venv/bin/python` exists and contains the installed requirements.
