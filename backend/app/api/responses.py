"""Reusable OpenAPI error-response declarations."""

from typing import Any

from backend.app.schemas.common import Error


BAD_REQUEST: dict[int, dict[str, Any]] = {
    400: {"model": Error, "description": "The request body is invalid."}
}
NOT_FOUND: dict[int, dict[str, Any]] = {
    404: {"model": Error, "description": "The requested resource was not found."}
}
CONFLICT: dict[int, dict[str, Any]] = {
    409: {
        "model": Error,
        "description": "The request conflicts with the current state of the resource.",
    }
}
