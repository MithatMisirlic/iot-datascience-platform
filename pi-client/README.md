# Raspberry Pi WebSocket Client

This directory is a self-contained Raspberry Pi deployment unit. It streams IMU, audio RMS, and optional JPEG camera frames to the configured WebSocket server. It does not import or access the REST backend, frontend, pipeline, or database.

## Deployment Scope

Deploy the contents of this `pi-client` directory directly to:

```text
/home/pi007/mithat-iot-datascience-platform
```

Do not deploy the repository's backend, frontend, pipeline, shared, or test directories to run the Pi client.

## Raspberry Pi Prerequisites

Install the system packages before running the setup script:

```bash
sudo apt update
sudo apt install -y \
  python3 python3-venv python3-pip python3-dev build-essential \
  i2c-tools alsa-utils libasound2-dev libportaudio2 portaudio19-dev
```

Enable I2C through `sudo raspi-config` under **Interface Options > I2C** before using the MPU6050. INMP441 I2S configuration depends on the selected audio HAT/overlay and must be completed separately.

## First-Time Setup

From the remote project directory:

```bash
cd /home/pi007/mithat-iot-datascience-platform
chmod +x setup_pi.sh
./setup_pi.sh
```

The script creates `.venv`, installs `requirements.txt`, creates `recordings`, copies `.env.example` to `.env` when needed, and makes `run_pi.sh` executable.

Review `.env`, then start the client:

```bash
./run_pi.sh
```

`run_pi.sh` loads `.env`, activates `.venv`, and runs:

```bash
python -m pi_client.main
```

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `PI_WS_HOST` | WebSocket server address | `192.168.0.182` |
| `PI_WS_PORT` | WebSocket server port | `8080` |
| `PI_WS_PATH` | WebSocket endpoint path | `/stream` |
| `PI_IMU_ENABLED` | Enable MPU6050 frames | `true` |
| `PI_AUDIO_ENABLED` | Enable audio RMS frames and WAV commands | `true` |
| `PI_CAMERA_ENABLED` | Enable JPEG camera frames | `false` |
| `PI_MOCK_MODE` | Use hardware-free mock recorders | `false` |
| `PI_IMU_RATE_HZ` | IMU frame rate | `60` |
| `PI_AUDIO_RATE_HZ` | Audio RMS frame rate | `60` |
| `PI_CAMERA_FPS` | Camera frame rate | `5` |
| `PI_WAV_DIR` | WAV output directory, relative to this directory | `./recordings` |

The remaining hardware and reconnect settings are documented in `.env.example`. All local paths are relative to the deployment directory.

## Testing Without Hardware

Set these values in `.env`:

```dotenv
PI_MOCK_MODE=true
PI_CAMERA_ENABLED=true
```

Then run `./run_pi.sh`. The client uses deterministic mock recorders but still requires a reachable WebSocket server. To test startup without a camera stream, leave `PI_CAMERA_ENABLED=false`.

## PyCharm Professional Deployment

### SFTP Deployment

1. Open **Settings > Build, Execution, Deployment > Deployment**.
2. Add an **SFTP** server using the Pi hostname/IP, SSH port, and user `pi007`.
3. Set the server root path to `/home/pi007/mithat-iot-datascience-platform`.
4. In **Mappings**, set the local path to this repository's `pi-client` directory and the deployment path to `/`.
5. Exclude `.venv`, `.env`, `recordings`, `__pycache__`, and `.idea` from deployment.
6. Upload the directory with **Tools > Deployment > Upload to...**.

This mapping is important: `setup_pi.sh`, `run_pi.sh`, and `requirements.txt` must be placed directly in the remote project root, not in a nested `pi-client` directory.

### Automatic Upload

Under **Settings > Build, Execution, Deployment > Deployment > Options**, set **Upload changed files automatically to the default server** to **Always** or **On explicit save action**. Mark the Pi SFTP entry as the default server.

### SSH Interpreter

Run `./setup_pi.sh` once before configuring the interpreter. Then:

1. Open **Settings > Project > Python Interpreter**.
2. Select **Add Interpreter > On SSH** and use the same Pi SSH connection.
3. Select the existing interpreter at `/home/pi007/mithat-iot-datascience-platform/.venv/bin/python`.
4. Set the remote working directory to `/home/pi007/mithat-iot-datascience-platform`.

### Remote Execution

The recommended remote run command is `./run_pi.sh` because it loads `.env`. Configure a PyCharm Shell Script run configuration with:

```text
Script: /home/pi007/mithat-iot-datascience-platform/run_pi.sh
Working directory: /home/pi007/mithat-iot-datascience-platform
```

Alternatively, use a Python run configuration with module `pi_client.main` and the same working directory. In that case, define the `PI_*` environment variables in the run configuration because Python execution does not automatically source `.env`.

## Expected Remote Layout

```text
/home/pi007/mithat-iot-datascience-platform/
├── .env
├── .env.example
├── .gitignore
├── .venv/
├── README.md
├── recordings/
├── requirements.txt
├── run_pi.sh
├── setup_pi.sh
└── pi_client/
    ├── __init__.py
    ├── main.py
    ├── websocket_client.py
    ├── config/
    ├── recorders/
    ├── storage/
    └── uploader/
```

## Troubleshooting

- `ModuleNotFoundError`: run `./setup_pi.sh` again and verify `.venv/bin/python` is selected.
- I2C permission errors: verify I2C is enabled and the user has access to `/dev/i2c-*`.
- Audio device errors: run `arecord -l` and verify the INMP441 I2S device configuration.
- WebSocket reconnect loop: verify `PI_WS_HOST`, `PI_WS_PORT`, network routing, and that the server exposes `/stream`.
- Camera import errors: keep `PI_CAMERA_ENABLED=false` until a supported camera stack is installed and configured.
