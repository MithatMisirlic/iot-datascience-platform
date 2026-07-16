"""Backend status display helpers."""

from __future__ import annotations

from frontend.api_client import ApiClientError, ExperimentApiClient


def render_backend_status(api: ExperimentApiClient) -> bool:
    """Render backend health and return whether the API is reachable."""

    import streamlit as st

    try:
        health = api.health()
    except ApiClientError as exc:
        st.error(f"Backend unavailable: {exc.message}")
        return False

    if health.get("status") == "healthy":
        st.success("Backend status: healthy")
        return True

    st.warning(f"Backend returned unexpected health payload: {health}")
    return False
