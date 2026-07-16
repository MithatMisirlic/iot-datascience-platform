"""Streamlit frontend configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FrontendSettings:
    """Runtime settings for the Streamlit dashboard."""

    api_base_url: str = "http://localhost:3000"
    api_timeout_seconds: float = 10.0


def get_settings() -> FrontendSettings:
    """Load frontend settings from environment variables."""

    base_url = os.getenv("API_BASE_URL", "http://localhost:3000").strip()
    timeout = os.getenv("API_TIMEOUT_SECONDS", "10").strip()
    try:
        timeout_seconds = float(timeout)
    except ValueError:
        timeout_seconds = 10.0

    return FrontendSettings(
        api_base_url=base_url.rstrip("/") or "http://localhost:3000",
        api_timeout_seconds=timeout_seconds,
    )
