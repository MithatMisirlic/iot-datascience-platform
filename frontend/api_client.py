"""Reusable HTTP client for the Experiment API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


JsonObject = dict[str, Any]


@dataclass(slots=True)
class ApiClientError(Exception):
    """User-facing API client error."""

    message: str
    status_code: int | None = None
    details: Any | None = None

    def __str__(self) -> str:
        return self.message


class ExperimentApiClient:
    """Small typed wrapper around the existing FastAPI contract."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
        )

    def close(self) -> None:
        """Close the underlying HTTP client when owned by this wrapper."""

        if self._owns_client:
            self._client.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: JsonObject | None = None,
        params: JsonObject | None = None,
    ) -> Any:
        """Perform one request and normalize backend errors."""

        try:
            response = self._client.request(
                method,
                path,
                json=json,
                params=params,
            )
        except httpx.TimeoutException as exc:
            raise ApiClientError("Backend request timed out.") from exc
        except httpx.RequestError as exc:
            raise ApiClientError(
                f"Could not connect to the backend at {self.base_url}."
            ) from exc

        if response.status_code >= 400:
            message, details = _parse_error_response(response)
            raise ApiClientError(
                message,
                status_code=response.status_code,
                details=details,
            )

        if response.status_code == 204:
            return None

        try:
            return response.json()
        except ValueError as exc:
            raise ApiClientError("Backend returned an invalid JSON response.") from exc

    def health(self) -> JsonObject:
        return self._request("GET", "/health")

    def create_experiment(self, payload: JsonObject) -> JsonObject:
        return self._request("POST", "/experiments", json=payload)

    def list_experiments(self, page: int = 1, page_size: int = 20) -> JsonObject:
        return self._request(
            "GET",
            "/experiments",
            params={"page": page, "pageSize": page_size},
        )

    def get_experiment(self, experiment_id: str) -> JsonObject:
        return self._request("GET", f"/experiments/{experiment_id}")

    def update_experiment(self, experiment_id: str, payload: JsonObject) -> JsonObject:
        return self._request("PATCH", f"/experiments/{experiment_id}", json=payload)

    def delete_experiment(self, experiment_id: str) -> None:
        self._request("DELETE", f"/experiments/{experiment_id}")

    def create_exercise(self, experiment_id: str, payload: JsonObject) -> JsonObject:
        return self._request(
            "POST",
            f"/experiments/{experiment_id}/exercises",
            json=payload,
        )

    def list_experiment_exercises(self, experiment_id: str) -> list[JsonObject]:
        return self._request("GET", f"/experiments/{experiment_id}/exercises")

    def list_exercises(self, page: int = 1, page_size: int = 20) -> JsonObject:
        return self._request(
            "GET",
            "/exercises",
            params={"page": page, "pageSize": page_size},
        )

    def get_exercise(self, exercise_id: str) -> JsonObject:
        return self._request("GET", f"/exercises/{exercise_id}")

    def delete_exercise(self, exercise_id: str) -> None:
        self._request("DELETE", f"/exercises/{exercise_id}")

    def start_recording(self, exercise_id: str) -> JsonObject:
        return self._request("POST", f"/exercises/{exercise_id}/recording/start")

    def stop_recording(self, exercise_id: str) -> JsonObject:
        return self._request("POST", f"/exercises/{exercise_id}/recording/stop")

    def get_exercise_data(self, exercise_id: str) -> JsonObject:
        return self._request("GET", f"/exercises/{exercise_id}/data")

    def clear_exercise_data(self, exercise_id: str) -> None:
        self._request("DELETE", f"/exercises/{exercise_id}/data")


def _parse_error_response(response: httpx.Response) -> tuple[str, Any]:
    """Extract the contract error shape without assuming valid JSON."""

    try:
        payload = response.json()
    except ValueError:
        return (
            f"Backend returned HTTP {response.status_code}.",
            response.text,
        )

    if isinstance(payload, dict):
        error = payload.get("error") or payload.get("detail")
        if isinstance(error, str) and error.strip():
            return error, payload

    return f"Backend returned HTTP {response.status_code}.", payload
