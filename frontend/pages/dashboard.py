"""Dashboard page."""

from __future__ import annotations

import streamlit as st

from frontend.api_client import ApiClientError, ExperimentApiClient
from frontend.components.forms import show_api_error
from frontend.components.status import render_backend_status


def render(api: ExperimentApiClient, base_url: str) -> None:
    """Render the dashboard landing page."""

    st.title("Experiment Platform Dashboard")
    st.write(
        "Operate the experiment workflow through the existing FastAPI REST API: "
        "manage experiments, create exercises, control recording state, and view "
        "processed research features."
    )

    col1, col2 = st.columns([1, 2])
    with col1:
        reachable = render_backend_status(api)
    with col2:
        st.info(f"API base URL: `{base_url}`")

    if not reachable:
        st.stop()

    with st.spinner("Loading dashboard summary..."):
        try:
            experiments = api.list_experiments(page=1, page_size=1)
            exercises = api.list_exercises(page=1, page_size=1)
        except ApiClientError as exc:
            show_api_error(exc)
            return

    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("Experiments", experiments.get("total", 0))
    metric2.metric("Exercises", exercises.get("total", 0))
    metric3.metric("Backend", "Healthy")

    st.subheader("Workflow")
    st.markdown(
        """
        1. Create or select an experiment.
        2. Add exercise recordings under that experiment.
        3. Start and stop recording using backend lifecycle endpoints.
        4. Process raw frames outside the dashboard when available.
        5. Review persisted results and clear data when re-recording is needed.
        """
    )


if __name__ == "__main__":
    from frontend.standalone import run_page

    run_page(render, "Dashboard")
