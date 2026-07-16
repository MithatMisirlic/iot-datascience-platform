"""Standalone runner for Streamlit native page execution."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from frontend.api_client import ExperimentApiClient
from frontend.config import get_settings


def run_page(render: Callable[[ExperimentApiClient, str], None], title: str) -> None:
    """Run one page when Streamlit executes a file in frontend/pages."""

    settings = get_settings()
    st.set_page_config(page_title=f"Experiment Platform - {title}", layout="wide")
    base_url = st.sidebar.text_input("API base URL", value=settings.api_base_url).rstrip("/")
    api = ExperimentApiClient(base_url=base_url, timeout=settings.api_timeout_seconds)
    try:
        render(api, base_url)
    finally:
        api.close()
