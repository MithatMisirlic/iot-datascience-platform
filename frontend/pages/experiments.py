"""Experiments management page."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from frontend.api_client import ApiClientError, ExperimentApiClient
from frontend.components.forms import (
    compact_payload,
    parse_optional_float,
    parse_optional_int,
    parse_properties_json,
    properties_to_json,
    show_api_error,
)
from frontend.state import reset_experiment_selection_if_invalid


def render(api: ExperimentApiClient, base_url: str) -> None:
    """Render experiment CRUD workflows."""

    del base_url
    st.title("Experiments")
    page = st.number_input("Page", min_value=1, value=1, step=1)
    page_size = st.selectbox("Page size", [10, 20, 50, 100], index=1)

    try:
        experiment_page = api.list_experiments(page=int(page), page_size=page_size)
    except ApiClientError as exc:
        show_api_error(exc)
        return

    items = experiment_page.get("items", [])
    reset_experiment_selection_if_invalid(
        st.session_state,
        {item["id"] for item in items if "id" in item},
    )

    st.caption(
        f"Showing page {experiment_page.get('page')} of "
        f"{experiment_page.get('total', 0)} experiments."
    )
    st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)

    tab_create, tab_edit, tab_delete = st.tabs(["Create", "View / Edit", "Delete"])
    with tab_create:
        _render_create_form(api)
    with tab_edit:
        _render_edit_form(api, items)
    with tab_delete:
        _render_delete_form(api, items)


def _experiment_payload(prefix: str, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    existing = existing or {}
    patient = st.text_input(
        "Patient number",
        value=str(existing.get("patientNumber", "")),
        key=f"{prefix}_patient",
    )
    age = st.text_input(
        "Age",
        value="" if existing.get("age") is None else str(existing.get("age")),
        key=f"{prefix}_age",
    )
    height = st.text_input(
        "Height",
        value="" if existing.get("height") is None else str(existing.get("height")),
        key=f"{prefix}_height",
    )
    weight = st.text_input(
        "Weight",
        value="" if existing.get("weight") is None else str(existing.get("weight")),
        key=f"{prefix}_weight",
    )
    properties = st.text_area(
        "Custom properties JSON",
        value=properties_to_json(existing.get("properties")),
        key=f"{prefix}_properties",
    )
    return compact_payload(
        {
            "patientNumber": patient.strip(),
            "age": parse_optional_int(age, "Age"),
            "height": parse_optional_float(height, "Height"),
            "weight": parse_optional_float(weight, "Weight"),
            "properties": parse_properties_json(properties),
        }
    )


def _render_create_form(api: ExperimentApiClient) -> None:
    with st.form("create_experiment"):
        try:
            payload = _experiment_payload("create")
        except ValueError as exc:
            st.warning(str(exc))
            payload = {}
        submitted = st.form_submit_button("Create experiment")

    if submitted:
        try:
            created = api.create_experiment(payload)
        except ApiClientError as exc:
            show_api_error(exc)
            return
        st.success(f"Created experiment {created['id']}.")
        st.session_state["selected_experiment_id"] = created["id"]
        st.rerun()


def _render_edit_form(api: ExperimentApiClient, items: list[dict[str, Any]]) -> None:
    if not items:
        st.info("No experiments available.")
        return
    selected = st.selectbox(
        "Experiment to edit",
        items,
        key="edit_experiment_select",
        format_func=lambda item: f"{item.get('patientNumber', 'no patient')} | {item['id']}",
    )
    st.json(selected)
    with st.form("edit_experiment"):
        try:
            payload = _experiment_payload("edit", selected)
        except ValueError as exc:
            st.warning(str(exc))
            payload = {}
        submitted = st.form_submit_button("Save changes")

    if submitted:
        try:
            updated = api.update_experiment(selected["id"], payload)
        except ApiClientError as exc:
            show_api_error(exc)
            return
        st.success(f"Updated experiment {updated['id']}.")
        st.rerun()


def _render_delete_form(api: ExperimentApiClient, items: list[dict[str, Any]]) -> None:
    if not items:
        st.info("No experiments available.")
        return
    selected = st.selectbox(
        "Experiment to delete",
        items,
        key="delete_experiment_select",
        format_func=lambda item: f"{item.get('patientNumber', 'no patient')} | {item['id']}",
    )
    st.warning("Deleting an experiment also deletes all related exercises and data.")
    confirmation = st.text_input(
        "Type the experiment ID to confirm deletion",
        key="delete_experiment_confirmation",
    )
    if st.button(
        "Delete experiment",
        disabled=confirmation != selected["id"],
        type="primary",
    ):
        try:
            api.delete_experiment(selected["id"])
        except ApiClientError as exc:
            show_api_error(exc)
            return
        st.session_state["selected_experiment_id"] = None
        st.session_state["selected_exercise_id"] = None
        st.success("Experiment deleted.")
        st.rerun()


if __name__ == "__main__":
    from frontend.standalone import run_page

    run_page(render, "Experiments")
