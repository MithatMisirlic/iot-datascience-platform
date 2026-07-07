"""FastAPI dependency providers."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.db.session import SessionLocal
from backend.app.integrations.recording import NoOpRecordingBackend, RecordingBackend
from backend.app.integrations.uploads import ArtifactStorage, LocalArtifactStorage


def get_db() -> Generator[Session, None, None]:
    """Provide one SQLAlchemy session for the lifetime of a request."""

    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()


DatabaseSession = Annotated[Session, Depends(get_db)]


_recording_backend = NoOpRecordingBackend()


def get_recording_backend() -> RecordingBackend:
    """Provide the configured external recording command adapter."""

    return _recording_backend


RecordingBackendDependency = Annotated[
    RecordingBackend,
    Depends(get_recording_backend),
]


_artifact_storage = LocalArtifactStorage(
    settings.resolved_upload_dir
)


def get_artifact_storage() -> ArtifactStorage:
    """Provide local artifact storage for cleanup and future upload routes."""

    return _artifact_storage


ArtifactStorageDependency = Annotated[
    ArtifactStorage,
    Depends(get_artifact_storage),
]
