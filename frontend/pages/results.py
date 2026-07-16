"""Processed results page."""

from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st


_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

from frontend.api_client import ApiClientError, ExperimentApiClient
from frontend.components.forms import show_api_error
from frontend.components.results import render_exercise_results
from frontend.page_helpers import select_exercise, select_experiment


def render(api: ExperimentApiClient, base_url: str) -> None:
    """Render stored ExerciseData-compatible results."""

    del base_url
    st.title("Results")
    st.caption("Review processed research features and export a descriptive report.")
    with st.expander("Demo mode: latest processed exercise", expanded=False):
        _render_latest_processed_result(api)

    experiment = select_experiment(api, "results_experiment_select")
    if experiment is None:
        return
    exercise = select_exercise(api, experiment["id"], "results_exercise_select")
    if exercise is None:
        return

    st.caption(f"Exercise ID: `{exercise['id']}`")
    fetch = st.button("Fetch processed data", type="primary")
    if fetch or st.session_state.get("last_results_exercise_id") == exercise["id"]:
        with st.spinner("Loading processed data..."):
            try:
                data = api.get_exercise_data(exercise["id"])
            except ApiClientError as exc:
                if exc.status_code == 404:
                    st.info(
                        "No processed data is available for this exercise yet. "
                        "Stop a recording from Live Experiment and wait for automatic "
                        "processing, or use the CLI fallback for sample data."
                    )
                else:
                    show_api_error(exc)
                return
        st.session_state["last_results_exercise_id"] = exercise["id"]
        render_exercise_results(data)

    st.divider()
    st.subheader("Clear Exercise Data")
    st.warning("Clearing data resets the exercise so it can be recorded again.")
    confirmation = st.text_input(
        "Type the exercise ID to confirm clearing data",
        key="clear_data_confirmation",
    )
    if st.button(
        "Clear data",
        disabled=confirmation != exercise["id"],
        type="primary",
    ):
        try:
            api.clear_exercise_data(exercise["id"])
        except ApiClientError as exc:
            show_api_error(exc)
            return
        st.session_state.pop("last_results_exercise_id", None)
        st.success("Exercise data cleared.")
        st.rerun()


def _render_latest_processed_result(api: ExperimentApiClient) -> None:
    """Load the newest exercise with data for hardware-free demonstration."""

    try:
        page = api.list_exercises(page=1, page_size=100)
    except ApiClientError as exc:
        show_api_error(exc)
        return
    exercises = page.get("items", []) if isinstance(page.get("items"), list) else []
    candidates = [item for item in exercises if item.get("hasData")]
    if not candidates:
        st.info("No processed exercise is available yet.")
        return
    latest = sorted(
        candidates,
        key=lambda item: item.get("recordingEndedAt") or item.get("createdAt") or "",
        reverse=True,
    )[0]
    st.caption(f"Latest processed exercise: `{latest['id']}`")
    if st.button("Load latest processed result"):
        try:
            data = api.get_exercise_data(latest["id"])
        except ApiClientError as exc:
            show_api_error(exc)
            return
        st.session_state["last_results_exercise_id"] = latest["id"]
        render_exercise_results(data)


if __name__ == "__main__":
    from frontend.standalone import run_page

    run_page(render, "Results")
