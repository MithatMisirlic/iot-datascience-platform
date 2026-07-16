"""Integration tests for file-backed raw-frame processing."""

from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.integrations.raw_frames import (
    LocalJsonRawFrameStorage,
    RawExerciseFrames,
)
from backend.app.models.exercise import Exercise
from backend.app.models.processed_result import ProcessedResult
from backend.app.services import processing_service
from shared.enums import RecordingStatus
from shared.errors import ResourceNotFoundError
from tools.process_exercise import sample_raw_frames


def create_exercise(client: TestClient) -> str:
    """Create and return one exercise through the existing public API."""
    experiment = client.post("/experiments", json={}).json()
    exercise = client.post(
        f"/experiments/{experiment['id']}/exercises",
        json={},
    ).json()
    return exercise["id"]


def test_raw_frames_can_be_saved_and_loaded(tmp_path: Path) -> None:
    storage = LocalJsonRawFrameStorage(tmp_path / "exercises")
    expected = sample_raw_frames()

    path = storage.save("exercise-1", expected)

    assert path == tmp_path / "exercises" / "exercise-1" / "raw_frames.json"
    assert storage.load("exercise-1") == expected
    assert "jpeg" not in path.read_text(encoding="utf-8")


def test_processing_persists_result_and_existing_get_returns_it(
    client: TestClient,
    database_session: Session,
    tmp_path: Path,
) -> None:
    exercise_id = create_exercise(client)
    storage = LocalJsonRawFrameStorage(tmp_path / "exercises")
    storage.save(exercise_id, sample_raw_frames())

    output = processing_service.process_raw_exercise(
        database_session,
        exercise_id,
        storage,
    )

    stored = database_session.scalar(
        select(ProcessedResult).where(ProcessedResult.exercise_id == exercise_id)
    )
    exercise = database_session.get(Exercise, exercise_id)
    assert stored is not None
    public_features = {
        key: output[key]
        for key in ("mouthOpening", "soundPressure", "footSpeed", "aggregates")
    }
    assert {
        key: stored.features[key]
        for key in ("mouthOpening", "soundPressure", "footSpeed", "aggregates")
    } == public_features
    assert set(stored.features["metadata"]["analysis"]) == {
        "audio",
        "movement",
        "vision",
        "overall",
    }
    assert exercise is not None
    assert exercise.hasData is True
    assert exercise.recordingStatus is RecordingStatus.STOPPED

    response = client.get(f"/exercises/{exercise_id}/data")
    assert response.status_code == 200
    assert response.json() == {
        key: output[key]
        for key in (
            "exerciseId",
            "startedAt",
            "endedAt",
            "mouthOpening",
            "soundPressure",
            "footSpeed",
            "aggregates",
        )
        if key in output
    }


def test_processing_missing_exercise_raises_clear_error(
    database_session: Session,
    tmp_path: Path,
) -> None:
    storage = LocalJsonRawFrameStorage(tmp_path / "exercises")

    with pytest.raises(ResourceNotFoundError, match="Exercise not found"):
        processing_service.process_raw_exercise(database_session, "missing", storage)


def test_processing_empty_raw_data_is_deterministic_and_valid(
    client: TestClient,
    database_session: Session,
    tmp_path: Path,
) -> None:
    exercise_id = create_exercise(client)
    storage = LocalJsonRawFrameStorage(tmp_path / "exercises")
    storage.save(exercise_id, RawExerciseFrames())

    output = processing_service.process_raw_exercise(
        database_session,
        exercise_id,
        storage,
    )

    assert output["mouthOpening"] == {"values": [], "sampleRate": 0.0}
    assert output["soundPressure"] == {"values": [], "sampleRate": 0.0}
    assert output["footSpeed"] == {
        "values": [],
        "sampleRate": 0.0,
        "unit": "cm/s",
    }
    assert output["aggregates"]["stepLengths"] == {
        "values": [],
        "unit": "cm",
    }
    assert output["metadata"]["analysis"]["overall"]["completeness"] == {
        "imu": 0.0,
        "audio": 0.0,
        "vision": 0.0,
    }
    public_output = {
        key: output[key]
        for key in (
            "exerciseId",
            "startedAt",
            "endedAt",
            "mouthOpening",
            "soundPressure",
            "footSpeed",
            "aggregates",
        )
        if key in output
    }
    assert client.get(f"/exercises/{exercise_id}/data").json() == public_output
