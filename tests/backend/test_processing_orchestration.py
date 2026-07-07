"""Tests for deferred and fake processed-result orchestration."""

from collections.abc import Sequence
from typing import Any

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.integrations.processing import ProcessingArtifact
from backend.app.models.processed_result import ProcessedResult
from backend.app.models.sensor_upload import SensorUpload
from backend.app.services import result_service
from shared.enums import SensorFileType
from shared.errors import (
    InvalidProcessedResultError,
    MissingArtifactsError,
    OperationDeferredError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from tests.backend.factories import processed_features


class FakeResultProcessor:
    """Return deterministic valid output and retain received descriptors."""

    required_file_types = frozenset(SensorFileType)

    def __init__(self) -> None:
        self.calls: list[tuple[str, Sequence[ProcessingArtifact]]] = []

    def process(
        self,
        exercise_id: str,
        artifacts: Sequence[ProcessingArtifact],
    ) -> dict[str, Any]:
        self.calls.append((exercise_id, artifacts))
        return processed_features()


class FailingResultProcessor(FakeResultProcessor):
    """Fail after input validation to test no-partial-result behavior."""

    def process(
        self,
        exercise_id: str,
        artifacts: Sequence[ProcessingArtifact],
    ) -> dict[str, Any]:
        del exercise_id, artifacts
        raise RuntimeError("processor failed")


class InvalidResultProcessor(FakeResultProcessor):
    """Return malformed output to test contract validation."""

    def process(
        self,
        exercise_id: str,
        artifacts: Sequence[ProcessingArtifact],
    ) -> dict[str, Any]:
        del exercise_id, artifacts
        return {"unexpected": True}


def create_exercise(client: TestClient, *, stop: bool = False) -> str:
    """Create an exercise and optionally finish its recording."""

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


def add_required_uploads(database: Session, exercise_id: str) -> None:
    """Persist one metadata row for every currently required sensor type."""

    database.add_all(
        [
            SensorUpload(
                exercise_id=exercise_id,
                file_type=file_type,
                original_filename=f"{file_type.value}.bin",
                file_path=f"{exercise_id}/{file_type.value}.bin",
            )
            for file_type in SensorFileType
        ]
    )
    database.commit()


def result_count(database: Session) -> int:
    """Return the number of persisted processed results."""

    return database.scalar(select(func.count()).select_from(ProcessedResult)) or 0


def test_processing_validates_exercise_state_and_required_uploads(
    client: TestClient,
    database_session: Session,
) -> None:
    """Reject missing exercises, active states, and incomplete artifacts."""

    processor = FakeResultProcessor()
    with pytest.raises(ResourceNotFoundError, match="Exercise not found"):
        result_service.process_exercise(database_session, "missing", processor)

    idle_exercise_id = create_exercise(client)
    with pytest.raises(ResourceConflictError, match="stopped recording"):
        result_service.process_exercise(
            database_session,
            idle_exercise_id,
            processor,
        )

    stopped_exercise_id = create_exercise(client, stop=True)
    with pytest.raises(MissingArtifactsError, match="Missing required artifacts"):
        result_service.process_exercise(
            database_session,
            stopped_exercise_id,
            processor,
        )
    assert processor.calls == []
    assert result_count(database_session) == 0


def test_deferred_processor_error_creates_no_result(
    client: TestClient,
    database_session: Session,
) -> None:
    """Raise the deferred error only after all processing inputs validate."""

    exercise_id = create_exercise(client, stop=True)
    add_required_uploads(database_session, exercise_id)

    with pytest.raises(OperationDeferredError, match="data pipeline"):
        result_service.process_exercise(database_session, exercise_id)
    assert result_count(database_session) == 0


def test_fake_processor_persists_result_and_existing_api_mapping(
    client: TestClient,
    database_session: Session,
) -> None:
    """Persist valid fake output and retrieve it through the existing API."""

    exercise_id = create_exercise(client, stop=True)
    add_required_uploads(database_session, exercise_id)
    processor = FakeResultProcessor()

    result = result_service.process_exercise(
        database_session,
        exercise_id,
        processor,
    )
    assert result.exercise_id == exercise_id
    assert result.features == processed_features()
    assert len(processor.calls) == 1
    received_types = {item.file_type for item in processor.calls[0][1]}
    assert received_types == set(SensorFileType)

    response = client.get(f"/exercises/{exercise_id}/data")
    assert response.status_code == 200
    assert response.json()["exerciseId"] == exercise_id
    assert response.json()["aggregates"] == processed_features()["aggregates"]


@pytest.mark.parametrize(
    ("processor", "error_type"),
    [
        (FailingResultProcessor(), RuntimeError),
        (InvalidResultProcessor(), InvalidProcessedResultError),
    ],
)
def test_processor_failure_or_invalid_output_creates_no_partial_result(
    client: TestClient,
    database_session: Session,
    processor: FakeResultProcessor,
    error_type: type[Exception],
) -> None:
    """Keep persistence empty when processing or output validation fails."""

    exercise_id = create_exercise(client, stop=True)
    add_required_uploads(database_session, exercise_id)

    with pytest.raises(error_type):
        result_service.process_exercise(database_session, exercise_id, processor)
    assert result_count(database_session) == 0
