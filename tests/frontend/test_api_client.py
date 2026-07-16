"""Tests for the Streamlit frontend API client."""

from __future__ import annotations

import httpx
import pytest

from frontend.api_client import ApiClientError, ExperimentApiClient


def make_client(handler: httpx.MockTransport) -> ExperimentApiClient:
    http_client = httpx.Client(base_url="http://testserver", transport=handler)
    return ExperimentApiClient("http://testserver", client=http_client)


def test_successful_api_response_parsing() -> None:
    """The client returns decoded JSON and sends contract query names."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/experiments"
        assert request.url.params["page"] == "2"
        assert request.url.params["pageSize"] == "5"
        return httpx.Response(
            200,
            json={"items": [{"id": "exp-1"}], "page": 2, "pageSize": 5, "total": 1},
        )

    api = make_client(httpx.MockTransport(handler))

    assert api.list_experiments(page=2, page_size=5)["items"] == [{"id": "exp-1"}]


def test_backend_error_parsing_uses_contract_error() -> None:
    """Contract error responses become user-facing exceptions."""

    api = make_client(
        httpx.MockTransport(
            lambda request: httpx.Response(404, json={"error": "Exercise not found."})
        )
    )

    with pytest.raises(ApiClientError) as error:
        api.get_exercise("missing")

    assert error.value.status_code == 404
    assert str(error.value) == "Exercise not found."
    assert error.value.details == {"error": "Exercise not found."}


def test_backend_non_json_error_is_safe() -> None:
    """Unexpected error bodies still produce a clear message."""

    api = make_client(
        httpx.MockTransport(lambda request: httpx.Response(500, text="broken"))
    )

    with pytest.raises(ApiClientError) as error:
        api.health()

    assert error.value.status_code == 500
    assert str(error.value) == "Backend returned HTTP 500."


def test_timeout_error_handling() -> None:
    """HTTP timeouts are normalized for display."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    api = make_client(httpx.MockTransport(handler))

    with pytest.raises(ApiClientError) as error:
        api.health()

    assert str(error.value) == "Backend request timed out."
    assert error.value.status_code is None


def test_connection_error_handling() -> None:
    """Connection failures do not leak low-level transport details."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    api = make_client(httpx.MockTransport(handler))

    with pytest.raises(ApiClientError) as error:
        api.health()

    assert "Could not connect to the backend" in str(error.value)


def test_delete_returns_none_for_no_content() -> None:
    """DELETE helpers accept the contract's 204 response."""

    api = make_client(httpx.MockTransport(lambda request: httpx.Response(204)))

    assert api.delete_exercise("exercise-1") is None
