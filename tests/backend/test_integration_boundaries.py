"""Tests for the deferred Raspberry Pi recording integration boundary."""

from fastapi.testclient import TestClient

from backend.app.dependencies import get_recording_backend
from backend.app.integrations.recording import NoOpRecordingBackend
from backend.app.main import app


class RecordingBackendSpy:
    """Capture recording commands without contacting external hardware."""

    def __init__(self) -> None:
        self.started: list[str] = []
        self.stopped: list[str] = []

    def start_recording(self, exercise_id: str) -> None:
        self.started.append(exercise_id)

    def stop_recording(self, exercise_id: str) -> None:
        self.stopped.append(exercise_id)


def create_exercise(client: TestClient) -> str:
    """Create one exercise through the public API."""

    experiment = client.post("/experiments", json={}).json()
    exercise = client.post(
        f"/experiments/{experiment['id']}/exercises",
        json={},
    ).json()
    return exercise["id"]


def test_default_recording_backend_requires_no_hardware(client: TestClient) -> None:
    """Run the complete lifecycle with the safe database-only adapter."""

    assert isinstance(get_recording_backend(), NoOpRecordingBackend)
    exercise_id = create_exercise(client)

    assert client.post(f"/exercises/{exercise_id}/recording/start").status_code == 200
    stopped = client.post(f"/exercises/{exercise_id}/recording/stop")
    assert stopped.status_code == 200
    assert stopped.json()["recordingStatus"] == "stopped"


def test_router_accepts_injected_recording_backend(client: TestClient) -> None:
    """Inject a future adapter without changing router or service signatures."""

    backend = RecordingBackendSpy()
    app.dependency_overrides[get_recording_backend] = lambda: backend
    exercise_id = create_exercise(client)

    assert client.post(f"/exercises/{exercise_id}/recording/start").status_code == 200
    assert backend.started == [exercise_id]

    conflict = client.post(f"/exercises/{exercise_id}/recording/start")
    assert conflict.status_code == 409
    assert backend.started == [exercise_id]

    assert client.post(f"/exercises/{exercise_id}/recording/stop").status_code == 200
    assert backend.stopped == [exercise_id]
