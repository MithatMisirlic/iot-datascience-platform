"""Recording lifecycle controls page."""

from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st


_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

from frontend.api_client import ApiClientError, ExperimentApiClient
from frontend.components.forms import show_api_error
from frontend.page_helpers import select_exercise, select_experiment


def render(api: ExperimentApiClient, base_url: str) -> None:
    """Render start/stop recording controls."""

    del base_url
    st.title("Recording Controls")
    experiment = select_experiment(api, "recording_experiment_select")
    if experiment is None:
        return
    exercise = select_exercise(api, experiment["id"], "recording_exercise_select")
    if exercise is None:
        return

    if st.button("Refresh exercise status"):
        st.rerun()

    try:
        current = api.get_exercise(exercise["id"])
    except ApiClientError as exc:
        show_api_error(exc)
        return

    status = current.get("recordingStatus", "unknown")
    has_data = bool(current.get("hasData"))
    cols = st.columns(4)
    cols[0].metric("Recording status", str(status))
    cols[1].metric("Has data", "yes" if has_data else "no")
    cols[2].metric("Started", str(current.get("recordingStartedAt") or "not started"))
    cols[3].metric("Ended", str(current.get("recordingEndedAt") or "not ended"))

    start_disabled = status == "recording" or has_data
    stop_disabled = status != "recording"
    action1, action2 = st.columns(2)
    with action1:
        if st.button("Start recording", disabled=start_disabled, type="primary"):
            try:
                updated = api.start_recording(current["id"])
            except ApiClientError as exc:
                show_api_error(exc)
                return
            st.success(f"Recording started for exercise {updated['id']}.")
            st.rerun()
    with action2:
        if st.button("Stop recording", disabled=stop_disabled):
            try:
                updated = api.stop_recording(current["id"])
            except ApiClientError as exc:
                show_api_error(exc)
                return
            st.success(f"Recording stopped for exercise {updated['id']}.")
            st.rerun()

    if has_data:
        st.info("Clear existing data on the Results page before re-recording.")
    elif status == "recording":
        st.warning("Recording is active according to the backend.")
    else:
        st.caption("No live sensor stream is shown in this dashboard.")


if __name__ == "__main__":
    from frontend.standalone import run_page

    run_page(render, "Recording")
