# Experiment Platform

A modular platform for collecting, processing, storing, and visualizing multimodal IoT experiment data. The project combines a Raspberry Pi sensor client, a FastAPI backend, a reusable data-processing pipeline, and a Streamlit dashboard.

The backend currently implements the approved OpenAPI contract, SQLite persistence, recording lifecycle state, local artifact storage scaffolding, and deferred processing orchestration. Hardware capture, public uploads, and real processing remain intentionally unavailable.

## Project Overview

The platform is designed for university experiments that capture synchronized motion, audio, and camera data. A Raspberry Pi records files locally and uploads them over HTTP. The backend manages experiment metadata and file ingestion, the pipeline extracts features, and the frontend presents sessions and results.

Primary goals:

- Keep hardware acquisition independent from backend persistence.
- Separate HTTP, business, persistence, and processing concerns.
- Support SQLite during development and PostgreSQL in a future deployment.
- Make individual components testable and independently replaceable.
- Provide a portfolio-quality foundation for local and remote deployment.

## Architecture

```text
Raspberry Pi client
  |  CSV / WAV / JPG over HTTP
  v
FastAPI backend  --->  File storage
  |                       |
  |                       v
  +-----------------> Data pipeline
  |                       |
  v                       v
SQLAlchemy database <--- Processed results
  ^
  |
Streamlit frontend ---> Backend REST API
```

The Pi client communicates only with the REST API and never accesses the database. The frontend follows the same boundary. Sensor processors live in the standalone pipeline package so processing code is not coupled to HTTP handlers or UI pages.

## Repository Structure

```text
experiment-platform/
|-- backend/
|   |-- alembic/                 # Future migration scripts
|   `-- app/
|       |-- api/v1/endpoints/    # Versioned REST endpoint modules
|       |-- core/                # Backend configuration and logging
|       |-- crud/                # Persistence operations
|       |-- db/                  # SQLAlchemy infrastructure
|       |-- dependencies/        # FastAPI dependency providers
|       |-- models/              # Database models
|       |-- schemas/             # API request and response schemas
|       |-- services/            # Use-case orchestration
|       |-- tasks/               # Background task integration points
|       `-- utils/               # Backend-specific utilities
|-- frontend/
|   |-- api/                     # Backend API client
|   |-- components/              # Reusable Streamlit components
|   `-- pages/                   # Dashboard pages
|-- pi-client/
|   `-- pi_client/
|       |-- config/              # Device configuration
|       |-- recorders/           # Hardware recording adapters
|       |-- storage/             # Local file management
|       `-- uploader/            # HTTP upload client
|-- pipeline/
|   |-- core/                    # Processing contracts
|   |-- features/                # Feature extraction
|   |-- io/                      # Pipeline input/output adapters
|   `-- processors/              # Sensor-specific processors
|-- shared/                      # Dependency-light shared contracts
|-- tools/                       # Standalone development utilities
|-- docs/                        # Architecture and operations guides
`-- tests/                       # Unit, component, and integration tests
```

## Installation

Prerequisites:

- Python 3.11 or newer
- Git
- PyCharm, or another Python IDE

Clone the repository and enter the project directory:

```bash
git clone <repository-url>
cd experiment-platform
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Activate it on Linux or macOS:

```bash
source .venv/bin/activate
```

Install runtime dependencies:

```bash
python -m pip install -r requirements.txt
```

Install test dependencies for local development:

```bash
python -m pip install -r requirements-dev.txt
```

## Development Setup

1. Copy `.env.example` to `.env` (`Copy-Item .env.example .env` on PowerShell).
2. Keep local secrets and machine-specific values in `.env`; it is ignored by Git.
3. Configure the repository root as the PyCharm project directory.
4. Select the `.venv` interpreter in PyCharm.
5. Run tests from the repository root with `python -m pytest`.

Pydantic Settings loads `.env` automatically. Environment variables override values in that file. Startup validates configuration, creates the SQLite parent directory and upload directory when needed, and then initializes database tables.

### Environment Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./data/experiment_platform.db` | SQLAlchemy database connection URL. |
| `UPLOAD_DIR` | `./data/uploads` | Root for locally stored recording artifacts. Filesystem roots are rejected. |
| `RAW_FRAME_DIR` | `./data/exercises` | Root for development raw-frame JSON documents. |
| `TESTING_MODE` | `false` | Identifies an isolated test runtime. |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`. |
| `PI_ADAPTER_MODE` | `noop` | Recording adapter selection. Only `noop` is accepted until Pi integration exists. |
| `CORS_ORIGINS` | Local ports `3000` and `8501` | Comma-separated browser origins. |

Tests set their configuration before importing the application and use in-memory SQLite plus a temporary upload root. They do not read or write the development database or upload directory.

## Backend

The `backend` package contains the FastAPI application, Pydantic contract schemas, SQLAlchemy models, database dependencies, and persistence operations. Experiment and exercise CRUD, recording lifecycle, and stored exercise-data retrieval/clearing are implemented. External recording commands, uploads, and result processing are isolated behind dependency-free integration ports; safe no-op/deferred adapters are used until the Raspberry Pi and pipeline are available.

Local artifact storage and `SensorUpload` metadata persistence are available as internal services. No public upload route is exposed because the authoritative OpenAPI contract does not define one; Raspberry Pi transport and automatic processing remain deferred.

Internal processing orchestration validates stopped recordings and required artifact metadata, delegates through `ResultProcessor`, validates output against `ExerciseData`, and persists `ProcessedResult` only after success. The default processor remains explicitly deferred; no real signal, audio, or video algorithms are included.

The development raw-frame workflow stores numeric IMU, audio RMS, and mouth geometry frames at `RAW_FRAME_DIR/<exercise-id>/raw_frames.json`. It does not store camera JPEG payloads in the database. To generate sample frames, process an existing exercise, and persist its `ProcessedResult`, run:

```bash
python -m tools.process_exercise <exercise-id> --generate-sample
```

The exercise must already exist in the configured database. Existing raw frames can be processed without replacing them by omitting `--generate-sample`. Verify the result through the unchanged endpoint:

```text
GET /exercises/<exercise-id>/data
```

Start the development server from the repository root:

```bash
uvicorn backend.app.main:app --reload --port 3000
```

Swagger UI is available at `http://localhost:3000/docs`.

Run the complete test suite:

```bash
python -m pytest -q
```

### Pi WebSocket Test Server

The development-only receiver in `tools/dev_ws_server.py` validates local Pi streaming without modifying or starting the REST API. From the repository root, with the development environment active, run:

```bash
python -m tools.dev_ws_server
```

It listens on all local interfaces at `ws://0.0.0.0:8080/stream` and prints IMU, audio, and camera frame counts once per second. Camera payloads remain in memory only long enough to count them; no images are written. The server sends no commands to the Pi.

Configure the Pi client's `PI_WS_HOST` with the development computer's LAN IP address, not `0.0.0.0` or `localhost`:

```dotenv
PI_WS_HOST=192.168.0.182
PI_WS_PORT=8080
PI_WS_PATH=/stream
```

Ensure the operating-system firewall permits inbound TCP port `8080`. Stop the server with `Ctrl+C`. Optional `--host` and `--port` arguments are available for local diagnostics, while the defaults match the Pi client protocol configuration.

## Frontend

The `frontend` package contains the Streamlit dashboard. It communicates only through the REST API using the reusable client in `frontend/api_client.py`; it does not import backend persistence, Pi client, or processing internals.

Dashboard pages include Dashboard, Experiments, Exercises, Recording, and Results. The UI supports experiment CRUD, exercise CRUD, recording start/stop controls, processed result visualization, and data clearing through the existing API contract.

Install dashboard dependencies:

```bash
python -m pip install -r frontend/requirements.txt
```

Configure the backend URL with `API_BASE_URL` or the sidebar input. The default is `http://localhost:3000`.

Start Streamlit from the repository root:

```bash
streamlit run frontend/app.py
```

See `frontend/README.md` for the full frontend setup and workflow.

## Pi Client

The `pi-client` directory is an independently deployable asyncio application. It streams raw MPU6050 frames, INMP441 RMS amplitude, and optional base64 JPEG frames to a configured WebSocket server. It also handles server-controlled local WAV start/stop commands and reconnects after connection failures.

Hardware adapters are guarded and replaceable with deterministic mocks. The client remains operationally and structurally independent from the REST backend and its database.

The backend currently permits only `PI_ADAPTER_MODE=noop`. A real mode will be added after the Pi command transport and failure behavior can be tested with hardware; changing the mode now fails configuration validation at startup.

## Pipeline

The `pipeline` package provides sensor-specific processing and reusable feature extraction. Planned processors cover accelerometer, gyroscope, audio, and camera data. Pipeline inputs and outputs are isolated behind adapters so processing remains testable without FastAPI or Streamlit.

## Database

Development uses SQLite through SQLAlchemy. Database access belongs exclusively to the backend persistence layer. Alembic is reserved for migrations as the implemented schema evolves.

PostgreSQL support is planned for remote deployment. Application code should depend on SQLAlchemy sessions rather than SQLite-specific behavior to preserve portability.

SQLite is appropriate for local development and a single backend process. Production deployment still requires migrations, PostgreSQL validation, authentication, TLS/reverse-proxy configuration, backups, and process supervision.

## Roadmap

- Connect recording lifecycle operations to the Raspberry Pi client.
- Populate processed exercise results through the data pipeline.
- Validate WebSocket streaming and recorder adapters on the Raspberry Pi hardware.
- Add processing workflows and feature extraction.
- Build the Streamlit dashboard and Plotly visualizations.
- Add unit, integration, and hardware-boundary tests.
- Introduce Alembic migrations, PostgreSQL, and Linux deployment automation.

## Contributing

Use focused branches and keep changes within component boundaries. New behavior should include type hints, package documentation, and tests. Avoid coupling the Pi client or frontend directly to backend database modules.

Before opening a pull request, run the available formatting, static analysis, and test commands documented by the project. These commands will be finalized when development tooling is selected.

## License

No open-source license has been selected yet. Until a license file is added, all rights are reserved by the project author.
