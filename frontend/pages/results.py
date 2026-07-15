"""Processed results page."""

from __future__ import annotations

import streamlit as st

from frontend.api_client import ApiClientError, ExperimentApiClient
from frontend.components.forms import show_api_error
from frontend.components.results import render_exercise_results
from frontend.page_helpers import select_exercise, select_experiment


def render(api: ExperimentApiClient, base_url: str) -> None:
    """Render stored ExerciseData-compatible results."""

    del base_url
    st.title("Results")
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
                        "Run the backend processing workflow first."
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


if __name__ == "__main__":
    from frontend.standalone import run_page

    run_page(render, "Results")
