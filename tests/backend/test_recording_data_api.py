"""Recording lifecycle and exercise-data endpoint tests."""

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.processed_result import ProcessedResult
from backend.app.models.sensor_upload import SensorUpload
from shared.enums import SensorFileType


def create_exercise(client: TestClient) -> tuple[str, str]:
    """Create an experiment and exercise for a lifecycle test."""

    experiment_response = client.post(
        "/experiments",
        json={"patientNumber": "P-recording"},
    )
    experiment_id = experiment_response.json()["id"]
    exercise_response = client.post(
        f"/experiments/{experiment_id}/exercises",
        json={"properties": {"condition": "test"}},
    )
    return experiment_id, exercise_response.json()["id"]


def test_start_recording_success_and_conflicts(client: TestClient) -> None:
    """Start recording and reject missing or already-recording exercises."""

    _, exercise_id = create_exercise(client)

    response = client.post(f"/exercises/{exercise_id}/recording/start")
    assert response.status_code == 200
    exercise = response.json()
    assert exercise["recordingStatus"] == "recording"
    assert exercise["hasData"] is False
    assert exercise["recordingStartedAt"] is not None
    assert exercise["recordingEndedAt"] is None
    assert datetime.fromisoformat(exercise["recordingStartedAt"]).tzinfo is not None

    response = client.post(f"/exercises/{exercise_id}/recording/start")
    assert response.status_code == 409
    assert response.json() == {"error": "Exercise is already recording."}

    response = client.post("/exercises/missing/recording/start")
    assert response.status_code == 404
    assert response.json() == {"error": "Exercise not found."}


def test_stop_recording_success_and_conflicts(client: TestClient) -> None:
    """Stop active recording and reject invalid stop/re-record transitions."""

    _, exercise_id = create_exercise(client)

    response = client.post("/exercises/missing/recording/stop")
    assert response.status_code == 404
    assert response.json() == {"error": "Exercise not found."}

    response = client.post(f"/exercises/{exercise_id}/recording/stop")
    assert response.status_code == 409
    assert response.json() == {"error": "Exercise is not currently recording."}

    start_response = client.post(f"/exercises/{exercise_id}/recording/start")
    response = client.post(f"/exercises/{exercise_id}/recording/stop")
    assert response.status_code == 200
    exercise = response.json()
    assert exercise["recordingStatus"] == "stopped"
    assert exercise["hasData"] is True
    assert exercise["recordingStartedAt"] == start_response.json()[
        "recordingStartedAt"
    ]
    assert exercise["recordingEndedAt"] is not None

    response = client.post(f"/exercises/{exercise_id}/recording/start")
    assert response.status_code == 409
    assert response.json() == {
        "error": "Exercise data must be cleared before recording again."
    }


def test_get_data_requires_recording_and_processed_result(client: TestClient) -> None:
    """Return 404 until both recorded and processed data are available."""

    _, exercise_id = create_exercise(client)

    response = client.get(f"/exercises/{exercise_id}/data")
    assert response.status_code == 404
    assert response.json() == {"error": "Exercise has no recorded data."}

    client.post(f"/exercises/{exercise_id}/recording/start")
    client.post(f"/exercises/{exercise_id}/recording/stop")
    response = client.get(f"/exercises/{exercise_id}/data")
    assert response.status_code == 404
    assert response.json() == {
        "error": "Processed exercise data is not available."
    }

    response = client.get("/exercises/missing/data")
    assert response.status_code == 404
    assert response.json() == {"error": "Exercise not found."}

    response = client.delete("/exercises/missing/data")
    assert response.status_code == 404
    assert response.json() == {"error": "Exercise not found."}


def test_get_and_clear_exercise_data(
    client: TestClient,
    database_session: Session,
) -> None:
    """Map stored JSON, delete internals, and reset exercise state."""

    _, exercise_id = create_exercise(client)
    start = client.post(f"/exercises/{exercise_id}/recording/start").json()
    stopped = client.post(f"/exercises/{exercise_id}/recording/stop").json()
    features = {
        "mouthOpening": {
            "values": [[0.1, 0.2], [0.2, 0.3]],
            "sampleRate": 30,
        },
        "soundPressure": {
            "values": [0.01, 0.02],
            "sampleRate": 48000,
            "unit": "Pa",
        },
        "footSpeed": {
            "values": [12.5, 13.0],
            "sampleRate": 100,
            "unit": "cm/s",
        },
        "aggregates": {
            "stepLengths": {"values": [42.0, 44.0], "unit": "cm"},
            "averages": {"footSpeed": 12.75, "stepLength": 43.0},
            "medians": {"footSpeed": 12.75, "stepLength": 43.0},
        },
    }
    database_session.add_all(
        [
            SensorUpload(
                exercise_id=exercise_id,
                file_type=SensorFileType.ACCEL,
                original_filename="accel.csv",
                file_path="recordings/accel.csv",
            ),
            ProcessedResult(exercise_id=exercise_id, features=features),
        ]
    )
    database_session.commit()

    response = client.get(f"/exercises/{exercise_id}/data")
    assert response.status_code == 200
    data = response.json()
    assert data["exerciseId"] == exercise_id
    assert data["startedAt"] == start["recordingStartedAt"]
    assert data["endedAt"] == stopped["recordingEndedAt"]
    assert data["mouthOpening"] == features["mouthOpening"]
    assert data["soundPressure"] == features["soundPressure"]
    assert data["footSpeed"] == features["footSpeed"]
    assert data["aggregates"] == features["aggregates"]

    response = client.delete(f"/exercises/{exercise_id}/data")
    assert response.status_code == 204
    assert response.content == b""

    exercise = client.get(f"/exercises/{exercise_id}").json()
    assert exercise["hasData"] is False
    assert exercise["recordingStatus"] == "idle"
    assert exercise["recordingStartedAt"] is None
    assert exercise["recordingEndedAt"] is None

    database_session.expire_all()
    upload_count = database_session.scalar(
        select(func.count()).select_from(SensorUpload)
    )
    result_count = database_session.scalar(
        select(func.count()).select_from(ProcessedResult)
    )
    assert upload_count == 0
    assert result_count == 0
