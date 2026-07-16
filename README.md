# IoT Data Science Platform

A modular university project for collecting, processing, storing, and visualizing multimodal exercise-recording data from a Raspberry Pi sensor setup.

The current system combines:

- Raspberry Pi client for sensor streaming.
- MPU6050 IMU for accelerometer and gyroscope frames.
- INMP441 microphone for RMS audio frames.
- Raspberry Pi CSI camera for base64 JPEG frames.
- Development WebSocket receiver for live frame-count validation.
- FastAPI backend for experiments, exercises, recording lifecycle, and processed data access.
- SQLAlchemy with SQLite for development persistence.
- Processing pipeline for generic IMU, audio, and mouth/MAR feature extraction.
- CLI processing workflow for creating persisted `ProcessedResult` rows.
- Streamlit dashboard for operating the REST workflow and viewing results.

This is not a medical device and does not provide diagnosis, treatment advice, or clinical predictions. Feature values are research/demo outputs only.

## Current Development Status

Implemented:

- FastAPI REST API with OpenAPI documentation.
- Experiment CRUD.
- Exercise CRUD.
- Recording start/stop lifecycle.
- Processed data retrieval and clearing.
- SQLite persistence.
- Streamlit dashboard.
- Raspberry Pi WebSocket streaming client.
- Development WebSocket receiver that counts live IMU/audio/camera frames.
- Processing pipeline and CLI integration for persisted results.

Current limitation:

- `tools.dev_ws_server` receives and counts live Pi frames, but it does not yet associate those frames with an exercise UUID.
- Live WebSocket frames are not yet automatically written to `RAW_FRAME_DIR/<exercise-id>/raw_frames.json`.
- `tools.process_exercise` is currently used to process stored or generated raw frames into `ProcessedResult.features`.

## Architecture

```text
Raspberry Pi sensors
  |-- MPU6050 IMU
  |-- INMP441 microphone
  `-- CSI camera
        |
        v
Pi WebSocket client
        |
        | ws://<development-machine-ip>:8080/stream
        v
Development WebSocket receiver
  tools.dev_ws_server
  - counts imu/audio/camera frames once per second
  - does not persist live frames yet
        |
        | current manual development bridge
        v
Raw frame JSON storage
  RAW_FRAME_DIR/<exercise-id>/raw_frames.json
        |
        v
Processing pipeline
  pipeline/core/process_exercise.py
        |
        v
ProcessedResult.features
  SQLite via SQLAlchemy
        |
        v
FastAPI REST API
  GET /exercises/{exerciseId}/data
        |
        v
Streamlit dashboard
  frontend/app.py
```

The Raspberry Pi client is independent from the backend database. The Streamlit dashboard also communicates only through the REST API.

## Extracted Analysis Features

These features support research exploration and demonstration. They are descriptive signal-analysis metrics only. They are not medical diagnoses, clinical scores, or Parkinson's disease classifiers.

### Audio / Speech Proxies

| Feature | Why it is useful | How it is computed |
| --- | --- | --- |
| RMS mean, min, max, standard deviation | Summarizes loudness/envelope variation across the recording. | Statistics over incoming `spl` RMS audio frames. |
| MFCC coefficient means and standard deviations | Provides compact cepstral summaries of the speech/audio envelope for research comparison. | Computes log-mel cepstral coefficients from the RMS envelope spectrum and summarizes the first 13 coefficients. |
| Zero crossing rate mean and maximum | Describes how often the centered audio envelope changes sign, a rough temporal variability measure. | Counts sign changes in sliding windows of the mean-centered RMS envelope. |
| Spectral centroid mean and maximum | Indicates where the envelope spectrum is concentrated. | Computes power-weighted average frequency from spectrogram columns. |
| Spectral bandwidth mean and maximum | Describes spread around the spectral centroid. | Computes power-weighted frequency deviation around each centroid. |
| Speech clarity proxy | Provides an explainable, non-clinical voiced-energy ratio. | Divides energy above the average RMS envelope by total RMS-envelope energy. |
| Syllable count, average syllable duration, syllables per second | Approximates timing of speech-like bursts. | Detects peaks in the RMS envelope and estimates active duration around each peak. |

### Movement / IMU Features

| Feature | Why it is useful | How it is computed |
| --- | --- | --- |
| Acceleration magnitude statistics | Summarizes motion intensity. | Converts raw MPU6050 accelerometer values using `raw / 16384.0` and computes vector magnitudes. |
| Gyroscope magnitude statistics | Summarizes rotational movement intensity. | Converts raw gyroscope values using `raw / 131.0` and computes vector magnitudes. |
| Step count | Provides a simple movement repetition estimate. | Detects peaks in acceleration magnitude using a prominence and distance threshold. |
| Cadence | Describes step frequency over time. | Converts detected steps and recording duration into steps per minute. |
| Movement variance, standard deviation, coefficient of variation | Describes movement consistency and variability. | Computes population statistics over acceleration magnitudes. |
| Gait speed proxy | Provides a comparable acceleration-derived movement proxy. | Scales mean dynamic acceleration relative to the median baseline; it is not physical walking speed. |
| Dominant frequency | Estimates the strongest periodic movement component. | Uses FFT on mean-centered acceleration magnitudes and reports the dominant non-DC frequency. |

### Vision / Mouth and Jaw Features

| Feature | Why it is useful | How it is computed |
| --- | --- | --- |
| Mouth opening | Describes vertical mouth movement. | Uses vertical mouth geometry samples from mouth/MAR frames. |
| Mouth width | Describes horizontal mouth movement. | Uses horizontal mouth geometry samples from mouth/MAR frames. |
| MAR | Normalizes mouth opening by width. | Computes `vertical / horizontal`, using zero when horizontal is zero. |
| Jaw movement amplitude | Describes overall jaw displacement in geometry units. | Computes maximum jaw-point displacement from the first processed jaw point. |
| Average jaw speed | Describes frame-to-frame jaw movement speed. | Computes point-to-point jaw displacement divided by timestamp delta. |
| Frame count and processed frame count | Shows vision data completeness. | Counts all vision frames and frames with usable face/mouth geometry. |

If MediaPipe Face Mesh is available in a future runtime, mouth and jaw landmark extraction can be connected behind the existing vision processor. In the current tested environment, MediaPipe is optional and safely guarded.

### Multi-Modal Report

| Feature | Why it is useful | How it is computed |
| --- | --- | --- |
| Experiment duration | Provides overall recording span. | Uses min/max timestamps across all available modalities. |
| Synchronization offsets | Shows timestamp alignment across sensors. | Compares earliest starts and latest ends for IMU, audio, and vision streams. |
| Sensor sample rates | Helps identify missing or slow data streams. | Estimates rate from timestamp spacing per modality. |
| Completeness metrics | Indicates which modalities produced data. | Reports modality-level presence and processed-frame ratio for vision. |
| Speech activity while moving | Describes overlap between audio activity and movement. | Counts aligned samples where sound pressure and acceleration are both above their modality means. |
| Average mouth opening during high movement | Describes mouth movement during higher acceleration periods. | Averages vertical mouth opening where acceleration magnitude is above its mean. |
| Processing timestamp | Records when processing ran. | Stores the UTC timestamp generated by the processing pipeline. |

## Repository Structure

```text
IoT_DataScience/
|-- backend/              # FastAPI app, SQLAlchemy models, services, schemas
|-- frontend/             # Streamlit dashboard and frontend API client
|-- pi-client/            # Raspberry Pi WebSocket client deployment unit
|-- pipeline/             # Pure Python processing and feature extraction
|-- shared/               # Dependency-light shared enums/errors/constants
|-- tools/                # Development WebSocket server and processing CLI
|-- tests/                # Backend, frontend, pipeline, Pi-client, and unit tests
|-- .env.example          # Backend/runtime environment placeholders
|-- requirements.txt      # Backend/runtime Python dependencies
`-- requirements-dev.txt  # Optional test/development dependency list
```

## Prerequisites

### Windows Development Machine

- Windows 10/11 or equivalent development environment.
- Python 3.11 or newer.
- Git.
- PowerShell.
- Optional: PyCharm Professional for SFTP deployment and SSH interpreter workflows.

### Raspberry Pi

- Raspberry Pi OS with Python 3.
- Raspberry Pi Zero-compatible setup, or another Pi with compatible I2C/I2S/camera support.
- MPU6050 connected over I2C.
- INMP441 microphone configured as an I2S audio input.
- Raspberry Pi camera connected and detected by `rpicam-hello --list-cameras`.
- Network connectivity from the Pi to the development machine running `tools.dev_ws_server`.

Install Pi system packages before running `setup_pi.sh`:

```bash
sudo apt update
sudo apt install -y \
  python3 python3-venv python3-pip python3-dev build-essential \
  i2c-tools alsa-utils libasound2-dev libportaudio2 portaudio19-dev \
  rpicam-apps python3-picamera2
```

On older Raspberry Pi OS releases, `libcamera-apps` may be used instead of `rpicam-apps`.

Enable I2C with:

```bash
sudo raspi-config
```

Then use **Interface Options > I2C**. Configure I2S audio according to your INMP441 wiring and overlay choice.

## Initial Setup

### Windows Development Setup

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r frontend/requirements.txt
python -m pip install pytest httpx
Copy-Item .env.example .env
Copy-Item frontend/.env.example frontend/.env
```

If PowerShell blocks activation scripts, run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

The backend reads `.env` from the repository root. The Streamlit dashboard reads `API_BASE_URL` from the process environment and also provides an API URL field in the sidebar.

### Raspberry Pi Setup

Deploy the contents of `pi-client/` to the Pi directory, for example:

```text
/home/pi007/mithat-iot-datascience-platform
```

From that Pi directory:

```bash
chmod +x setup_pi.sh
./setup_pi.sh
```

Edit `.env` and set the WebSocket host to the IP address of the development machine running `tools.dev_ws_server`. Then start the Pi client:

```bash
./run_pi.sh
```

PyCharm SFTP deployment is optional. Manual copy, `scp`, Git checkout, or rsync are also valid as long as `setup_pi.sh`, `run_pi.sh`, `requirements.txt`, `.env.example`, and `pi_client/` are placed directly in the Pi deployment directory.

## Environment Variables

### Backend and Processing

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./data/experiment_platform.db` | SQLAlchemy database URL. |
| `UPLOAD_DIR` | `./data/uploads` | Local artifact storage root. Must not be a filesystem root. |
| `RAW_FRAME_DIR` | `./data/exercises` | Raw-frame JSON root used by `tools.process_exercise`. |
| `TESTING_MODE` | `false` | Marks isolated test runtime. |
| `LOG_LEVEL` | `INFO` | Backend logging level. |
| `PI_ADAPTER_MODE` | `noop` | Backend recording adapter mode. Only `noop` is currently supported. |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:8501` | Comma-separated allowed browser origins. |

### Frontend

| Variable | Default | Purpose |
| --- | --- | --- |
| `API_BASE_URL` | `http://localhost:3000` | FastAPI backend base URL used by Streamlit. |
| `API_TIMEOUT_SECONDS` | `10` | Frontend HTTP timeout. |

### Raspberry Pi Client

| Variable | Default | Purpose |
| --- | --- | --- |
| `PI_WS_HOST` | `192.168.0.182` | Development machine IP or hostname for the WebSocket receiver. |
| `PI_WS_PORT` | `8080` | WebSocket receiver port. |
| `PI_WS_PATH` | `/stream` | WebSocket path. |
| `PI_IMU_ENABLED` | `true` | Enable MPU6050 IMU frames. |
| `PI_AUDIO_ENABLED` | `true` | Enable microphone RMS frames and WAV command handling. |
| `PI_CAMERA_ENABLED` | `false` | Enable camera JPEG frames. |
| `PI_MOCK_MODE` | `false` | Use mock recorders instead of real hardware. |
| `PI_IMU_RATE_HZ` | `60` | IMU frame target rate. |
| `PI_AUDIO_RATE_HZ` | `60` | Audio RMS frame target rate. |
| `PI_CAMERA_FPS` | `5` | Camera frame target rate. |
| `PI_RECONNECT_INITIAL_SECONDS` | `1` | Initial WebSocket reconnect delay. |
| `PI_RECONNECT_MAX_SECONDS` | `30` | Maximum WebSocket reconnect delay. |
| `PI_I2C_BUS` | `1` | I2C bus for MPU6050. |
| `PI_MPU6050_ADDRESS` | `0x68` | MPU6050 I2C address. |
| `PI_AUDIO_SAMPLE_RATE` | `48000` | Audio capture sample rate. |
| `PI_CAMERA_INDEX` | `0` | OpenCV fallback camera index. |
| `PI_CAMERA_JPEG_QUALITY` | `80` | JPEG quality for camera frames. |
| `PI_WAV_DIR` | `./recordings` | Local WAV output directory for `start_wav`/`stop_wav` commands. |

Do not commit real passwords, SSH keys, server credentials, or private network credentials.

## Exact Run Order

Use separate terminals from the repository root on the development machine.

### Terminal 1: FastAPI Backend

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 3000
```

### Terminal 2: Development WebSocket Receiver

```bash
python -m tools.dev_ws_server
```

Expected output includes:

```text
Development WebSocket server listening on ws://0.0.0.0:8080/stream
Outbound Pi commands are disabled.
frames/s imu=0 audio=0 camera=0
```

### Terminal 3: Streamlit Dashboard

```bash
streamlit run frontend/app.py
```

### Raspberry Pi

From the Pi deployment directory:

```bash
./run_pi.sh
```

The Pi must use the development machine LAN IP for `PI_WS_HOST`, not `0.0.0.0` and usually not `localhost`.

## End-to-End Demonstration

1. Open Streamlit at `http://localhost:8501`.
2. Confirm the dashboard reports a healthy backend.
3. Create an experiment on the Experiments page.
4. Create an exercise on the Exercises page.
5. Copy the real exercise UUID shown by the dashboard.
6. Start recording on the Recording page.
7. Confirm Terminal 2 shows incoming Pi frame counts for IMU, audio, and/or camera.
8. Stop recording on the Recording page.
9. Process sample raw frames for the exercise:

```bash
python -m tools.process_exercise <exercise-id> --generate-sample
```

Replace `<exercise-id>` with the real exercise UUID, for example:

```bash
python -m tools.process_exercise 11111111-2222-3333-4444-555555555555 --generate-sample
```

Do not use the placeholder UUID unless such an exercise really exists in your database. If the UUID is wrong, the CLI reports that the exercise was not found.

10. Open the Results page in Streamlit.
11. Select the same experiment and exercise.
12. Click **Fetch processed data**.
13. Confirm charts, sample counts, and aggregate values display.

Important: the `--generate-sample` command writes deterministic sample raw frames for the selected exercise. It does not process the live frames counted by `tools.dev_ws_server`. Automatic live-frame persistence is a future integration step.

## Verification URLs

- Backend health: `http://localhost:3000/health`
- Swagger UI: `http://localhost:3000/docs`
- Streamlit dashboard: `http://localhost:8501`

## Testing

Run the full test suite from the repository root:

```bash
python -m pytest -q
```

The current verified test count is listed in the final validation report for each documentation/update pass, because it can change as tests are added.

## Troubleshooting

### `ModuleNotFoundError: No module named 'frontend'`

Run Streamlit from the repository root with the exact command:

```bash
streamlit run frontend/app.py
```

Do not run `python frontend/app.py`. The frontend includes a small path bootstrap for Streamlit script execution, so manual `PYTHONPATH` changes should not be required.

### WebSocket Connection Refused

Start the development receiver first:

```bash
python -m tools.dev_ws_server
```

Verify the Pi `.env` uses:

```dotenv
PI_WS_PORT=8080
PI_WS_PATH=/stream
```

Check Windows Firewall and allow inbound TCP port `8080`.

### Wrong Laptop IP

`PI_WS_HOST` must be the development machine IP reachable from the Pi. On Windows, find it with:

```powershell
ipconfig
```

Use the IPv4 address for the active Wi-Fi/Ethernet adapter. Do not set `PI_WS_HOST=0.0.0.0` on the Pi.

### Camera Not Detected

On the Pi, run:

```bash
rpicam-hello --list-cameras
```

If no camera appears, check the ribbon cable, camera enablement, Pi OS camera stack, and power supply.

### Picamera2 Missing From Venv

Install the system package and rerun setup:

```bash
sudo apt install -y python3-picamera2 rpicam-apps
./setup_pi.sh
```

If Picamera2 is still unavailable inside the virtual environment, use `PI_MOCK_MODE=true` or keep `PI_CAMERA_ENABLED=false` until the Pi camera stack is fixed.

### Stale PyCharm Deployment Files

If the Pi runs old code, delete stale remote files or re-upload the full `pi-client/` directory. Ensure `setup_pi.sh`, `run_pi.sh`, and `requirements.txt` are directly under `/home/pi007/mithat-iot-datascience-platform`, not nested under another `pi-client` directory.

### Exercise Not Found When Processing

The CLI requires a real exercise UUID from the current SQLite database:

```bash
python -m tools.process_exercise <exercise-id> --generate-sample
```

Create the exercise through Streamlit or the API first, then copy its actual UUID.

### No Results in Streamlit

`GET /exercises/{exerciseId}/data` returns data only after a `ProcessedResult` exists. Run:

```bash
python -m tools.process_exercise <exercise-id> --generate-sample
```

Then refresh the Results page and click **Fetch processed data**.

## Known Limitations

- Live WebSocket frame persistence is not yet wired automatically to exercise IDs.
- The processing CLI is currently separate from recording stop.
- `tools.dev_ws_server` is a development receiver, not production deployment infrastructure.
- Foot speed is currently an acceleration-derived research placeholder, not validated physical speed.
- No medical diagnosis, clinical scoring, or treatment recommendation is provided.
- No authentication or multi-user authorization is implemented.
- SQLite is used for local development; production needs database migration and PostgreSQL validation.

## Development Notes

- Keep backend, frontend, Pi client, and pipeline boundaries separate.
- Do not let the Pi client access the database directly.
- Do not import backend persistence modules into Streamlit.
- Keep hardware access isolated in `pi-client/` recorders.
- Keep processing deterministic and testable without hardware.

## License

No open-source license has been selected yet. Until a license file is added, all rights are reserved by the project author.
