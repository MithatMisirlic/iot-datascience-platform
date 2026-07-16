"""Live recording session manager and automatic processing tests."""

from __future__ import annotations

from pathlib import Path
from threading import Thread

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.integrations.raw_frames import LocalJsonRawFrameStorage
from backend.app.main import app
from backend.app.models.processed_result import ProcessedResult
from backend.app.services import processing_service
from backend.app.services.live_recording_session import LiveRecordingSessionManager, live_recording_manager


def create_exercise(client: TestClient) -> str:
    experiment = client.post("/experiments", json={}).json()
    exercise = client.post(f"/experiments/{experiment['id']}/exercises", json={}).json()
    return exercise["id"]


def imu_frame(ts: float = 1.0) -> dict[str, object]:
    return {
        "type": "imu",
        "ts": ts,
        "accel_x": 16384,
        "accel_y": 0,
        "accel_z": 0,
        "gyro_x": 131,
        "gyro_y": 0,
        "gyro_z": 0,
    }


def audio_frame(ts: float = 1.0) -> dict[str, object]:
    return {"type": "audio", "ts": ts, "spl": 0.25}


def mouth_frame(ts: float = 1.0) -> dict[str, object]:
    return {
        "type": "mouth",
        "ts": ts,
        "vertical": 0.2,
        "horizontal": 0.5,
        "mar": 0.4,
    }


def test_starting_recording_activates_correct_exercise_session(client: TestClient) -> None:
    exercise_id = create_exercise(client)

    response = client.post(f"/exercises/{exercise_id}/recording/start")

    assert response.status_code == 200
    snapshot = live_recording_manager.snapshot()
    assert snapshot["recordingState"] == "recording"
    assert snapshot["activeExerciseId"] == exercise_id


def test_idle_frames_are_not_persisted(tmp_path: Path) -> None:
    manager = LiveRecordingSessionManager()
    manager.receive_frame(imu_frame())

    frames = manager.stop_recording("exercise-1")
    path = LocalJsonRawFrameStorage(tmp_path).save("exercise-1", frames)
    loaded = LocalJsonRawFrameStorage(tmp_path).load("exercise-1")

    assert path.is_file()
    assert loaded.imu == ()


def test_recording_frames_are_associated_with_active_exercise(tmp_path: Path) -> None:
    manager = LiveRecordingSessionManager()
    manager.start_recording("exercise-1")
    manager.receive_frame(imu_frame(1.0))
    manager.receive_frame(audio_frame(1.1))
    manager.receive_frame(mouth_frame(1.2))

    frames = manager.stop_recording("exercise-1")
    storage = LocalJsonRawFrameStorage(tmp_path)
    storage.save("exercise-1", frames)
    loaded = storage.load("exercise-1")

    assert loaded.imu[0]["accel_x"] == 16384
    assert loaded.audio[0]["spl"] == 0.25
    assert loaded.mouth[0]["vertical"] == 0.2


def test_stopping_finalizes_storage_and_persists_processed_result(
    client: TestClient,
    database_session: Session,
) -> None:
    exercise_id = create_exercise(client)
    assert client.post(f"/exercises/{exercise_id}/recording/start").status_code == 200
    live_recording_manager.receive_frame(imu_frame(1.0))
    live_recording_manager.receive_frame(audio_frame(1.0))
    live_recording_manager.receive_frame(mouth_frame(1.0))

    response = client.post(f"/exercises/{exercise_id}/recording/stop")

    assert response.status_code == 200
    result = database_session.scalar(
        select(ProcessedResult).where(ProcessedResult.exercise_id == exercise_id)
    )
    assert result is not None
    assert result.features["metadata"]["analysis"]["overall"]["completeness"] == {
        "imu": 1.0,
        "audio": 1.0,
        "vision": 1.0,
    }
    assert client.get(f"/exercises/{exercise_id}/data").status_code == 200


def test_mocked_websocket_end_to_end_recording(client: TestClient) -> None:
    exercise_id = create_exercise(client)
    assert client.post(f"/exercises/{exercise_id}/recording/start").status_code == 200

    with client.websocket_connect("/stream") as websocket:
        websocket.send_json(imu_frame(1.0))
        websocket.send_json(audio_frame(1.0))
        websocket.send_json(mouth_frame(1.0))

    response = client.post(f"/exercises/{exercise_id}/recording/stop")
    data = client.get(f"/exercises/{exercise_id}/data")

    assert response.status_code == 200
    assert data.status_code == 200
    assert data.json()["mouthOpening"]["values"] == [[0.2, 0.5]]
    assert data.json()["soundPressure"]["values"] == [0.25]
    assert data.json()["footSpeed"]["values"] == [100.0]


def test_processing_failure_retains_raw_data(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exercise_id = create_exercise(client)
    client.post(f"/exercises/{exercise_id}/recording/start")
    live_recording_manager.receive_frame(imu_frame())

    def fail_processing(*args: object, **kwargs: object) -> None:
        raise RuntimeError("processor failed")

    monkeypatch.setattr(processing_service, "process_raw_exercise", fail_processing)
    response = client.post(f"/exercises/{exercise_id}/recording/stop")

    assert response.status_code == 409
    assert response.json() == {
        "error": "Recording stopped, but automatic processing failed. Raw data was retained."
    }
    exercise = client.get(f"/exercises/{exercise_id}").json()
    assert exercise["recordingStatus"] == "stopped"
    storage = LocalJsonRawFrameStorage(settings.resolved_raw_frame_dir)
    assert len(storage.load(exercise_id).imu) == 1
    assert live_recording_manager.snapshot()["recordingState"] == "error"


def test_camera_preview_is_throttled() -> None:
    manager = LiveRecordingSessionManager(preview_min_interval_seconds=10.0)
    manager.start_recording("exercise-1")
    manager.receive_frame({"type": "camera", "ts": 1.0, "jpeg": "first"})
    manager.receive_frame({"type": "camera", "ts": 1.1, "jpeg": "second"})

    snapshot = manager.snapshot()

    assert snapshot["latest"]["camera"]["jpeg"] == "first"
    assert snapshot["frameCounts"]["camera"] == 2


def test_session_state_is_thread_safe_for_single_pi_setup() -> None:
    manager = LiveRecordingSessionManager()
    manager.start_recording("exercise-1")

    def send_frames() -> None:
        for index in range(20):
            manager.receive_frame(imu_frame(float(index)))

    threads = [Thread(target=send_frames) for _ in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=2)

    frames = manager.stop_recording("exercise-1")

    assert len(frames.imu) == 60
    assert manager.snapshot()["recordingState"] == "processing"


def test_public_openapi_operations_remain_unchanged() -> None:
    operations = sorted(
        (method.upper(), path)
        for path, item in app.openapi()["paths"].items()
        for method in item
        if method in {"get", "post", "patch", "delete", "put"}
    )

    assert operations == [
        ("DELETE", "/exercises/{exerciseId}"),
        ("DELETE", "/exercises/{exerciseId}/data"),
        ("DELETE", "/experiments/{experimentId}"),
        ("GET", "/"),
        ("GET", "/exercises"),
        ("GET", "/exercises/{exerciseId}"),
        ("GET", "/exercises/{exerciseId}/data"),
        ("GET", "/experiments"),
        ("GET", "/experiments/{experimentId}"),
        ("GET", "/experiments/{experimentId}/exercises"),
        ("GET", "/health"),
        ("PATCH", "/experiments/{experimentId}"),
        ("POST", "/exercises/{exerciseId}/recording/start"),
        ("POST", "/exercises/{exerciseId}/recording/stop"),
        ("POST", "/experiments"),
        ("POST", "/experiments/{experimentId}/exercises"),
    ]
