# Experiment Platform

A modular platform for collecting, processing, storing, and visualizing multimodal IoT experiment data. The project combines a Raspberry Pi sensor client, a FastAPI backend, a reusable data-processing pipeline, and a Streamlit dashboard.

This repository currently contains the approved architecture and development setup only. Application behavior will be implemented incrementally.

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

1. Copy `.env.example` to `.env`.
2. Keep local secrets and machine-specific values in `.env`; it is ignored by Git.
3. Configure the repository root as the PyCharm project directory.
4. Select the `.venv` interpreter in PyCharm.
5. Run tests from the repository root with `python -m pytest`.

The sample environment uses local-only addresses and SQLite. It contains no credentials or private keys.

## Backend

The `backend` package contains the FastAPI application, Pydantic contract schemas, SQLAlchemy models, database dependencies, and persistence operations. Experiment and exercise CRUD endpoints are implemented; recording-control and exercise-data endpoints remain explicit `501 Not Implemented` placeholders.

Start the development server from the repository root:

```bash
uvicorn backend.app.main:app --reload --port 3000
```

Swagger UI is available at `http://localhost:3000/docs`.

## Frontend

The `frontend` package is reserved for the Streamlit dashboard. Pages are separated from reusable components and backend API access. The frontend will communicate through HTTP and will not import backend persistence code.

Planned pages include Dashboard, Experiments, Participants, Recording Sessions, Results, and Analytics.

## Pi Client

The `pi-client` directory is an independently deployable Raspberry Pi application. Its responsibilities are limited to recording MPU6050 motion data, INMP441 audio, and camera images; storing files locally; and uploading them to the backend over HTTP.

The client must remain operationally and structurally independent from the backend database.

## Pipeline

The `pipeline` package provides sensor-specific processing and reusable feature extraction. Planned processors cover accelerometer, gyroscope, audio, and camera data. Pipeline inputs and outputs are isolated behind adapters so processing remains testable without FastAPI or Streamlit.

## Database

Development uses SQLite through SQLAlchemy. Database access belongs exclusively to the backend persistence layer. Alembic is reserved for migrations as the implemented schema evolves.

PostgreSQL support is planned for remote deployment. Application code should depend on SQLAlchemy sessions rather than SQLite-specific behavior to preserve portability.

## Roadmap

- Implement recording-control behavior behind the existing contract endpoints.
- Implement exercise-data retrieval and clearing.
- Implement local Pi sensor recording and resilient HTTP uploads.
- Add processing workflows and feature extraction.
- Build the Streamlit dashboard and Plotly visualizations.
- Add unit, integration, and hardware-boundary tests.
- Introduce Alembic migrations, PostgreSQL, and Linux deployment automation.

## Contributing

Use focused branches and keep changes within component boundaries. New behavior should include type hints, package documentation, and tests. Avoid coupling the Pi client or frontend directly to backend database modules.

Before opening a pull request, run the available formatting, static analysis, and test commands documented by the project. These commands will be finalized when development tooling is selected.

## License

No open-source license has been selected yet. Until a license file is added, all rights are reserved by the project author.
