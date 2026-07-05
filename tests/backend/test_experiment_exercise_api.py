"""Persistence tests for experiment and exercise contract endpoints."""

from uuid import UUID

from fastapi.testclient import TestClient


def test_experiment_and_exercise_crud_lifecycle(client: TestClient) -> None:
    """Exercise the implemented CRUD flow and parent cascade."""

    experiment_payload = {
        "patientNumber": "P-0042",
        "height": 176,
        "age": 63,
        "weight": 78.5,
        "properties": {"room": "Lab 2"},
    }
    response = client.post("/experiments", json=experiment_payload)
    assert response.status_code == 201
    experiment = response.json()
    experiment_id = experiment["id"]
    UUID(experiment_id)
    assert experiment["patientNumber"] == "P-0042"

    response = client.get("/experiments", params={"page": 1, "pageSize": 1})
    assert response.status_code == 200
    assert response.json() == {
        "items": [experiment],
        "page": 1,
        "pageSize": 1,
        "total": 1,
    }

    response = client.get(f"/experiments/{experiment_id}")
    assert response.status_code == 200
    assert response.json() == experiment

    response = client.patch(
        f"/experiments/{experiment_id}",
        json={"weight": 80, "properties": {"notes": "updated"}},
    )
    assert response.status_code == 200
    updated_experiment = response.json()
    assert updated_experiment["weight"] == 80
    assert updated_experiment["age"] == 63
    assert updated_experiment["properties"] == {"notes": "updated"}

    response = client.post(
        f"/experiments/{experiment_id}/exercises",
        json={"properties": {"condition": "baseline"}},
    )
    assert response.status_code == 201
    exercise = response.json()
    exercise_id = exercise["id"]
    UUID(exercise_id)
    assert exercise["experimentId"] == experiment_id
    assert exercise["recordingStatus"] == "idle"
    assert exercise["hasData"] is False

    response = client.get(f"/experiments/{experiment_id}/exercises")
    assert response.status_code == 200
    assert response.json() == [exercise]

    response = client.get("/exercises", params={"page": 1, "pageSize": 20})
    assert response.status_code == 200
    assert response.json() == {
        "items": [exercise],
        "page": 1,
        "pageSize": 20,
        "total": 1,
    }

    response = client.get(f"/exercises/{exercise_id}")
    assert response.status_code == 200
    assert response.json() == exercise

    response = client.delete(f"/exercises/{exercise_id}")
    assert response.status_code == 204
    assert response.content == b""
    response = client.get(f"/exercises/{exercise_id}")
    assert response.status_code == 404
    assert response.json() == {"error": "Exercise not found."}

    response = client.post(
        f"/experiments/{experiment_id}/exercises",
        json={},
    )
    cascade_exercise_id = response.json()["id"]
    response = client.delete(f"/experiments/{experiment_id}")
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/experiments/{experiment_id}").status_code == 404
    assert client.get(f"/exercises/{cascade_exercise_id}").status_code == 404


def test_contract_errors(client: TestClient) -> None:
    """Verify validation errors and missing parent behavior."""

    response = client.post("/experiments", json={"age": "invalid"})
    assert response.status_code == 400
    assert response.json() == {"error": "The request is invalid."}

    response = client.post("/experiments/missing/exercises", json={})
    assert response.status_code == 404
    assert response.json() == {"error": "Experiment not found."}

    response = client.get("/experiments/missing/exercises")
    assert response.status_code == 404
    assert response.json() == {"error": "Experiment not found."}

    response = client.get("/experiments", params={"page": 0})
    assert response.status_code == 400
    assert response.json() == {"error": "The request is invalid."}

def test_experiment_and_exercise_pagination(client: TestClient) -> None:
    """Verify page offsets, limits, and total counts for both resources."""

    experiment_ids: list[str] = []
    for number in range(3):
        response = client.post(
            "/experiments",
            json={"patientNumber": f"P-{number}"},
        )
        assert response.status_code == 201
        experiment_ids.append(response.json()["id"])

    response = client.get("/experiments", params={"page": 2, "pageSize": 2})
    assert response.status_code == 200
    experiment_page = response.json()
    assert experiment_page["page"] == 2
    assert experiment_page["pageSize"] == 2
    assert experiment_page["total"] == 3
    assert len(experiment_page["items"]) == 1

    for experiment_id in experiment_ids:
        response = client.post(f"/experiments/{experiment_id}/exercises", json={})
        assert response.status_code == 201

    response = client.get("/exercises", params={"page": 2, "pageSize": 2})
    assert response.status_code == 200
    exercise_page = response.json()
    assert exercise_page["page"] == 2
    assert exercise_page["pageSize"] == 2
    assert exercise_page["total"] == 3
    assert len(exercise_page["items"]) == 1
