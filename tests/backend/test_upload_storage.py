"""Tests for internal recording-artifact storage scaffolding."""

from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.dependencies import get_artifact_storage
from backend.app.integrations.uploads import LocalArtifactStorage
from backend.app.main import app
from backend.app.models.processed_result import ProcessedResult
from backend.app.models.sensor_upload import SensorUpload
from backend.app.services import upload_service
from shared.enums import SensorFileType
from shared.errors import (
    InvalidArtifactError,
    OperationDeferredError,
    ResourceConflictError,
    ResourceNotFoundError,
    UnsupportedArtifactError,
)


@pytest.fixture
def storage(client: TestClient, tmp_path: Path) -> LocalArtifactStorage:
    """Use isolated local storage for service and API cleanup operations."""

    del client
    local_storage = LocalArtifactStorage(tmp_path / "uploads")
    app.dependency_overrides[get_artifact_storage] = lambda: local_storage
    return local_storage


def create_exercise(client: TestClient, *, stop: bool = False) -> str:
    """Create an exercise and optionally complete its recording lifecycle."""

    experiment = client.post("/experiments", json={}).json()
    exercise = client.post(
        f"/experiments/{experiment['id']}/exercises",
        json={},
    ).json()
    exercise_id = exercise["id"]
    if stop:
        client.post(f"/exercises/{exercise_id}/recording/start")
        client.post(f"/exercises/{exercise_id}/recording/stop")
    return exercise_id


def upload_artifact(
    database: Session,
    storage: LocalArtifactStorage,
    exercise_id: str,
    content: bytes = b"acceleration-data",
) -> SensorUpload:
    """Store one valid accelerometer artifact through the upload service."""

    return upload_service.receive_sensor_upload(
        database,
        exercise_id,
        SensorFileType.ACCEL,
        "accel.csv",
        BytesIO(content),
        storage,
    )


def test_successful_artifact_storage_and_metadata_persistence(
    client: TestClient,
    database_session: Session,
    storage: LocalArtifactStorage,
) -> None:
    """Store bytes locally and persist matching internal metadata."""

    exercise_id = create_exercise(client, stop=True)
    upload = upload_artifact(database_session, storage, exercise_id)

    stored_path = storage.root / upload.file_path
    assert stored_path.read_bytes() == b"acceleration-data"
    assert upload.exercise_id == exercise_id
    assert upload.file_type is SensorFileType.ACCEL
    assert upload.original_filename == "accel.csv"

    persisted = database_session.get(SensorUpload, upload.id)
    assert persisted is not None
    assert persisted.file_path == upload.file_path
    result_count = database_session.scalar(
        select(func.count()).select_from(ProcessedResult)
    )
    assert result_count == 0


def test_upload_validates_exercise_state_type_and_content(
    client: TestClient,
    database_session: Session,
    storage: LocalArtifactStorage,
) -> None:
    """Reject missing ownership, invalid state, type, filename, and content."""

    with pytest.raises(ResourceNotFoundError, match="Exercise not found"):
        upload_artifact(database_session, storage, "missing")

    idle_exercise_id = create_exercise(client)
    with pytest.raises(ResourceConflictError, match="recording has stopped"):
        upload_artifact(database_session, storage, idle_exercise_id)

    exercise_id = create_exercise(client, stop=True)
    with pytest.raises(UnsupportedArtifactError, match="not supported"):
        upload_service.receive_sensor_upload(
            database_session,
            exercise_id,
            "temperature",  # type: ignore[arg-type]
            "temperature.csv",
            BytesIO(b"data"),
            storage,
        )
    with pytest.raises(InvalidArtifactError, match="filename"):
        upload_service.receive_sensor_upload(
            database_session,
            exercise_id,
            SensorFileType.ACCEL,
            "",
            BytesIO(b"data"),
            storage,
        )
    with pytest.raises(InvalidArtifactError, match="empty"):
        upload_artifact(database_session, storage, exercise_id, b"")


def test_default_upload_receiver_remains_deferred(
    client: TestClient,
    database_session: Session,
) -> None:
    """Keep transport/storage integration explicit when no adapter is supplied."""

    exercise_id = create_exercise(client, stop=True)
    with pytest.raises(OperationDeferredError, match="Pi upload flow"):
        upload_service.receive_sensor_upload(
            database_session,
            exercise_id,
            SensorFileType.AUDIO,
            "audio.wav",
            BytesIO(b"audio-data"),
        )


def test_exercise_delete_cleans_file_and_metadata(
    client: TestClient,
    database_session: Session,
    storage: LocalArtifactStorage,
) -> None:
    """Remove local artifacts when their parent exercise is deleted."""

    exercise_id = create_exercise(client, stop=True)
    upload = upload_artifact(database_session, storage, exercise_id)
    upload_id = upload.id
    stored_path = storage.root / upload.file_path
    assert stored_path.exists()

    response = client.delete(f"/exercises/{exercise_id}")
    assert response.status_code == 204
    assert not stored_path.exists()
    database_session.expire_all()
    assert database_session.get(SensorUpload, upload_id) is None


def test_clear_data_cleans_file_and_preserves_exercise(
    client: TestClient,
    database_session: Session,
    storage: LocalArtifactStorage,
) -> None:
    """Remove artifacts through data cleanup while retaining the exercise."""

    exercise_id = create_exercise(client, stop=True)
    upload = upload_artifact(database_session, storage, exercise_id)
    stored_path = storage.root / upload.file_path

    response = client.delete(f"/exercises/{exercise_id}/data")
    assert response.status_code == 204
    assert not stored_path.exists()
    exercise = client.get(f"/exercises/{exercise_id}").json()
    assert exercise["recordingStatus"] == "idle"
    assert exercise["hasData"] is False
