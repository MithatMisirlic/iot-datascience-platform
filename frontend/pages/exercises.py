"""Exercise management page."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st


_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

from frontend.api_client import ApiClientError, ExperimentApiClient
from frontend.components.forms import (
    parse_properties_json,
    properties_to_json,
    show_api_error,
)
from frontend.page_helpers import exercise_label, select_experiment
from frontend.state import reset_exercise_selection_if_invalid


def render(api: ExperimentApiClient, base_url: str) -> None:
    """Render exercise CRUD workflows."""

    del base_url
    st.title("Exercises")
    experiment = select_experiment(api, "exercises_experiment_select")
    if experiment is None:
        return

    try:
        exercises = api.list_experiment_exercises(experiment["id"])
    except ApiClientError as exc:
        show_api_error(exc)
        return

    reset_exercise_selection_if_invalid(
        st.session_state,
        {exercise["id"] for exercise in exercises if "id" in exercise},
    )

    st.subheader("Exercises for Selected Experiment")
    st.dataframe(pd.DataFrame(exercises), use_container_width=True, hide_index=True)

    tab_create, tab_details, tab_delete = st.tabs(["Create", "Details", "Delete"])
    with tab_create:
        _render_create_exercise(api, experiment["id"])
    with tab_details:
        _render_exercise_details(exercises)
    with tab_delete:
        _render_delete_exercise(api, exercises)


def _render_create_exercise(api: ExperimentApiClient, experiment_id: str) -> None:
    with st.form("create_exercise"):
        properties = st.text_area("Custom properties JSON", value="{}")
        submitted = st.form_submit_button("Create exercise")

    if submitted:
        try:
            payload = {"properties": parse_properties_json(properties)}
            created = api.create_exercise(experiment_id, payload)
        except ValueError as exc:
            st.warning(str(exc))
            return
        except ApiClientError as exc:
            show_api_error(exc)
            return
        st.session_state["selected_exercise_id"] = created["id"]
        st.success(f"Created exercise {created['id']}.")
        st.rerun()


def _render_exercise_details(exercises: list[dict[str, object]]) -> None:
    if not exercises:
        st.info("No exercises available.")
        return
    selected = st.selectbox(
        "Exercise",
        exercises,
        key="exercise_details_select",
        format_func=exercise_label,
    )
    st.session_state["selected_exercise_id"] = selected["id"]
    cols = st.columns(4)
    cols[0].metric("Status", str(selected.get("recordingStatus", "unknown")))
    cols[1].metric("Has data", "yes" if selected.get("hasData") else "no")
    cols[2].metric("Created", str(selected.get("createdAt", ""))[:19])
    cols[3].metric("Experiment", str(selected.get("experimentId", ""))[:8])
    st.json(selected)
    st.text_area(
        "Properties",
        value=properties_to_json(selected.get("properties")),
        disabled=True,
    )


def _render_delete_exercise(
    api: ExperimentApiClient,
    exercises: list[dict[str, object]],
) -> None:
    if not exercises:
        st.info("No exercises available.")
        return
    selected = st.selectbox(
        "Exercise to delete",
        exercises,
        key="delete_exercise_select",
        format_func=exercise_label,
    )
    confirmation = st.text_input(
        "Type the exercise ID to confirm deletion",
        key="delete_exercise_confirmation",
    )
    if st.button(
        "Delete exercise",
        disabled=confirmation != selected["id"],
        type="primary",
    ):
        try:
            api.delete_exercise(str(selected["id"]))
        except ApiClientError as exc:
            show_api_error(exc)
            return
        st.session_state["selected_exercise_id"] = None
        st.success("Exercise deleted.")
        st.rerun()


if __name__ == "__main__":
    from frontend.standalone import run_page

    run_page(render, "Exercises")
