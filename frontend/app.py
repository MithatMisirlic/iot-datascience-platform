"""Streamlit application entry point."""

from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st


_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

from frontend.api_client import ExperimentApiClient
from frontend.config import get_settings
from frontend.pages import dashboard, exercises, experiments, recording, results


PAGES = {
    "Dashboard": dashboard.render,
    "Experiments": experiments.render,
    "Exercises": exercises.render,
    "Recording": recording.render,
    "Results": results.render,
}


def main() -> None:
    """Run the Streamlit dashboard."""

    settings = get_settings()
    st.set_page_config(
        page_title="Experiment Platform",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.sidebar.title("Experiment Platform")
    st.sidebar.caption("Backend-driven research workflow dashboard")
    base_url = st.sidebar.text_input(
        "API base URL",
        value=st.session_state.get("api_base_url", settings.api_base_url),
    ).rstrip("/")
    st.session_state["api_base_url"] = base_url

    page_name = st.sidebar.radio("Navigation", list(PAGES), key="navigation")
    st.sidebar.divider()
    st.sidebar.caption("No authentication is configured for this university demo.")

    api = ExperimentApiClient(
        base_url=base_url,
        timeout=settings.api_timeout_seconds,
    )
    try:
        PAGES[page_name](api, base_url)
    finally:
        api.close()


if __name__ == "__main__":
    main()
