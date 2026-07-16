"""Reusable form helpers for Streamlit pages."""

from __future__ import annotations

import json
from typing import Any

from frontend.api_client import ApiClientError


def parse_properties_json(text: str) -> dict[str, str]:
    """Parse custom properties from a JSON object string."""

    text = text.strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Properties must be valid JSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError("Properties must be a JSON object.")
    invalid = [
        key
        for key, value in payload.items()
        if not isinstance(key, str) or not isinstance(value, str)
    ]
    if invalid:
        raise ValueError("Properties must contain string keys and string values.")
    return payload


def compact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove empty optional values before sending a patch/create payload."""

    compact: dict[str, Any] = {}
    for key, value in payload.items():
        if value is None or value == "":
            continue
        compact[key] = value
    return compact


def show_api_error(error: ApiClientError) -> None:
    """Display a backend/client error in Streamlit."""

    import streamlit as st

    prefix = f"HTTP {error.status_code}: " if error.status_code else ""
    st.error(f"{prefix}{error.message}")


def properties_to_json(value: Any) -> str:
    """Return formatted JSON for editing custom string properties."""

    if isinstance(value, dict):
        return json.dumps(value, indent=2, sort_keys=True)
    return "{}"


def parse_optional_float(value: str, field_name: str) -> float | None:
    """Parse an optional floating-point form value."""

    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a number.") from exc


def parse_optional_int(value: str, field_name: str) -> int | None:
    """Parse an optional integer form value."""

    value = value.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an integer.") from exc
