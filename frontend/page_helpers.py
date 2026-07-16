"""Shared Streamlit page helpers."""

from __future__ import annotations

from typing import Any

from frontend.api_client import ApiClientError, ExperimentApiClient
from frontend.components.forms import show_api_error


def load_experiments(api: ExperimentApiClient) -> list[dict[str, Any]]:
    """Load up to one page of experiments for dashboard selections."""

    page = api.list_experiments(page=1, page_size=100)
    items = page.get("items", [])
    return items if isinstance(items, list) else []


def load_exercises(api: ExperimentApiClient) -> list[dict[str, Any]]:
    """Load up to one page of exercises for dashboard selections."""

    page = api.list_exercises(page=1, page_size=100)
    items = page.get("items", [])
    return items if isinstance(items, list) else []


def experiment_label(experiment: dict[str, Any]) -> str:
    """Return a compact label for an experiment selectbox."""

    patient = experiment.get("patientNumber") or "no patient number"
    return f"{patient} | {experiment.get('id')}"


def exercise_label(exercise: dict[str, Any]) -> str:
    """Return a compact label for an exercise selectbox."""

    status = exercise.get("recordingStatus", "unknown")
    data = "data" if exercise.get("hasData") else "no data"
    return f"{status} | {data} | {exercise.get('id')}"


def select_experiment(api: ExperimentApiClient, key: str) -> dict[str, Any] | None:
    """Render an experiment selector and return the selected item."""

    import streamlit as st

    try:
        experiments = load_experiments(api)
    except ApiClientError as exc:
        show_api_error(exc)
        return None

    if not experiments:
        st.info("Create an experiment before using this workflow.")
        return None

    ids = [experiment["id"] for experiment in experiments]
    current = st.session_state.get("selected_experiment_id")
    index = ids.index(current) if current in ids else 0
    selected = st.selectbox(
        "Experiment",
        experiments,
        index=index,
        key=key,
        format_func=experiment_label,
    )
    st.session_state["selected_experiment_id"] = selected["id"]
    return selected


def select_exercise(
    api: ExperimentApiClient,
    experiment_id: str,
    key: str,
) -> dict[str, Any] | None:
    """Render an exercise selector for one experiment."""

    import streamlit as st

    try:
        exercises = api.list_experiment_exercises(experiment_id)
    except ApiClientError as exc:
        show_api_error(exc)
        return None

    if not exercises:
        st.info("Create an exercise for this experiment first.")
        return None

    ids = [exercise["id"] for exercise in exercises]
    current = st.session_state.get("selected_exercise_id")
    index = ids.index(current) if current in ids else 0
    selected = st.selectbox(
        "Exercise",
        exercises,
        index=index,
        key=key,
        format_func=exercise_label,
    )
    st.session_state["selected_exercise_id"] = selected["id"]
    return selected
