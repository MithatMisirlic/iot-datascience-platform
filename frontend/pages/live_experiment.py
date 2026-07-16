"""Guided live experiment workflow page."""

from __future__ import annotations

import base64
from pathlib import Path
import sys
import time
from typing import Any

import pandas as pd
import streamlit as st


_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

from frontend.api_client import ApiClientError, ExperimentApiClient
from frontend.components.forms import show_api_error
from frontend.live_client import LiveStateClient, websocket_url_from_api_base
from frontend.page_helpers import select_exercise, select_experiment


def render(api: ExperimentApiClient, base_url: str) -> None:
    """Render a single guided live recording workflow."""
    st.title("Live Experiment")
    st.caption("Guided recording workflow for one exercise and one connected Raspberry Pi.")
    live_client = _get_live_client(base_url)
    state = live_client.snapshot()

    experiment = select_experiment(api, "live_experiment_select")
    if experiment is None:
        _render_live_state(state)
        return
    exercise = select_exercise(api, experiment["id"], "live_exercise_select")
    if exercise is None:
        _render_live_state(state)
        return

    try:
        current = api.get_exercise(exercise["id"])
    except ApiClientError as exc:
        show_api_error(exc)
        return

    _render_experiment_summary(experiment, current, state)
    _render_controls(api, current)
    _render_live_state(state)

    if (
        current.get("hasData")
        or st.session_state.get("processing_completed_exercise_id") == current["id"]
    ):
        st.success("Processing completed successfully. Results are ready.")
        if st.button("View Results", type="primary"):
            st.session_state["navigation"] = "Results"
            st.session_state["last_results_exercise_id"] = current["id"]
            st.rerun()

    if st.toggle("Auto-refresh every second", value=False):
        time.sleep(1.0)
        st.rerun()


def _get_live_client(base_url: str) -> LiveStateClient:
    websocket_url = websocket_url_from_api_base(base_url)
    existing = st.session_state.get("live_state_client")
    if (
        not isinstance(existing, LiveStateClient)
        or existing.websocket_url != websocket_url
    ):
        if isinstance(existing, LiveStateClient):
            existing.stop()
        existing = LiveStateClient(websocket_url)
        existing.start()
        st.session_state["live_state_client"] = existing
    return existing


def _render_experiment_summary(
    experiment: dict[str, Any],
    exercise: dict[str, Any],
    state: dict[str, Any],
) -> None:
    st.subheader("Experiment Summary")
    exercise_name = _exercise_name(exercise)
    experiment_name = experiment.get("patientNumber") or experiment.get("id", "n/a")
    cols = st.columns(4)
    cols[0].markdown(
        _status_badge("Pi", "connected" if state["piConnected"] else "disconnected"),
        unsafe_allow_html=True,
    )
    cols[1].markdown(
        _status_badge("Recording", str(exercise.get("recordingStatus", "unknown"))),
        unsafe_allow_html=True,
    )
    cols[2].markdown(
        _status_badge("Processing", str(state.get("recordingState", "idle"))),
        unsafe_allow_html=True,
    )
    cols[3].metric("Duration", f"{state['elapsedRecordingSeconds']:.1f}s")
    detail_cols = st.columns(4)
    detail_cols[0].metric("Experiment", str(experiment_name))
    detail_cols[1].metric("Exercise", exercise_name)
    detail_cols[2].metric("Has data", "yes" if exercise.get("hasData") else "no")
    detail_cols[3].metric("Timestamp", time.strftime("%H:%M:%S"))
    with st.expander("Identifiers and timestamps", expanded=False):
        st.write(
            {
                "experimentId": experiment.get("id"),
                "exerciseId": exercise.get("id"),
                "createdAt": exercise.get("createdAt"),
                "recordingStartedAt": exercise.get("recordingStartedAt"),
                "recordingEndedAt": exercise.get("recordingEndedAt"),
                "activeExerciseId": state.get("activeExerciseId"),
            }
        )
    if state.get("lastError"):
        st.error(f"Processing failed: {state['lastError']}")


def _render_controls(api: ExperimentApiClient, exercise: dict[str, Any]) -> None:
    status = exercise.get("recordingStatus")
    has_data = bool(exercise.get("hasData"))
    start_disabled = status == "recording" or has_data
    stop_disabled = status != "recording"
    left, middle, right = st.columns(3)
    with left:
        if st.button("Start Recording", disabled=start_disabled, type="primary"):
            try:
                api.start_recording(exercise["id"])
            except ApiClientError as exc:
                show_api_error(exc)
                return
            st.success("Recording started.")
            st.rerun()
    with middle:
        if st.button("Stop and Process", disabled=stop_disabled):
            with st.spinner("Stopping recording and processing stored frames..."):
                try:
                    api.stop_recording(exercise["id"])
                except ApiClientError as exc:
                    show_api_error(exc)
                    return
            st.session_state["processing_completed_exercise_id"] = exercise["id"]
            st.success("Processing completed successfully.")
            st.rerun()
    with right:
        if st.button("Refresh status"):
            st.rerun()


def _render_live_state(state: dict[str, Any]) -> None:
    latest = state.get("latest", {})
    frame_rates = state.get("frameRates", {})
    frame_counts = state.get("frameCounts", {})

    st.divider()
    st.subheader("Live Monitoring")
    _render_sensor_indicators(latest, frame_rates, frame_counts)
    camera_tab, audio_tab, imu_tab, vision_tab = st.tabs(
        ["Camera", "Audio", "IMU", "Vision"]
    )
    with camera_tab:
        _render_camera(latest.get("camera"), frame_rates.get("camera", 0.0))
    with audio_tab:
        _render_audio(latest.get("audio"), frame_rates.get("audio", 0.0))
    with imu_tab:
        _render_imu(latest.get("imu"), frame_rates.get("imu", 0.0))
    with vision_tab:
        _render_mouth(latest.get("mouth"), frame_rates.get("mouth", 0.0))


def _render_sensor_indicators(
    latest: dict[str, Any],
    frame_rates: dict[str, Any],
    frame_counts: dict[str, Any],
) -> None:
    cols = st.columns(4)
    for column, sensor in zip(cols, ("imu", "audio", "camera", "mouth"), strict=True):
        healthy = isinstance(latest.get(sensor), dict)
        rate = float(frame_rates.get(sensor, 0.0) or 0.0)
        count = int(frame_counts.get(sensor, 0) or 0)
        state = "healthy" if healthy and rate > 0 else "waiting" if count > 0 else "disconnected"
        column.markdown(_status_badge(sensor.upper(), state), unsafe_allow_html=True)
        column.caption(f"{rate:.1f} Hz | {count} frames")


def _render_camera(camera: Any, fps: float) -> None:
    st.markdown("#### Camera Preview")
    st.caption(f"Preview rate: {fps:.1f} FPS. Frames are throttled and not persisted.")
    if not isinstance(camera, dict) or not isinstance(camera.get("jpeg"), str):
        st.info("No camera preview available.")
        return
    try:
        st.image(base64.b64decode(camera["jpeg"]), caption="Latest throttled preview")
    except Exception:
        st.warning("Latest camera preview could not be decoded.")


def _render_audio(audio: Any, rate: float) -> None:
    st.markdown("#### Audio Level")
    value = float(audio.get("spl", 0.0)) if isinstance(audio, dict) else 0.0
    st.metric("Current SPL/RMS", f"{value:.3f}")
    st.caption(f"Audio rate: {rate:.1f} Hz")
    _append_rolling("live_audio_values", value)
    st.line_chart(pd.DataFrame({"spl": st.session_state["live_audio_values"]}))


def _render_imu(imu: Any, rate: float) -> None:
    st.markdown("#### IMU Values")
    if not isinstance(imu, dict):
        st.info("No IMU frame available.")
        return
    ax = float(imu.get("accel_x", 0.0))
    ay = float(imu.get("accel_y", 0.0))
    az = float(imu.get("accel_z", 0.0))
    gx = float(imu.get("gyro_x", 0.0))
    gy = float(imu.get("gyro_y", 0.0))
    gz = float(imu.get("gyro_z", 0.0))
    accel_magnitude = ((ax * ax + ay * ay + az * az) ** 0.5) / 16384.0
    cols = st.columns(4)
    cols[0].metric("Accel X", f"{ax:.0f}")
    cols[1].metric("Accel Y", f"{ay:.0f}")
    cols[2].metric("Accel Z", f"{az:.0f}")
    cols[3].metric("IMU Hz", f"{rate:.1f}")
    st.caption(f"Gyro raw: x={gx:.0f}, y={gy:.0f}, z={gz:.0f}")
    _append_rolling("live_accel_magnitude", accel_magnitude)
    st.line_chart(pd.DataFrame({"accel_magnitude_g": st.session_state["live_accel_magnitude"]}))


def _render_mouth(mouth: Any, rate: float) -> None:
    st.markdown("#### Vision / Mouth")
    if not isinstance(mouth, dict):
        st.info("No mouth/MAR frame available.")
        return
    vertical = float(mouth.get("vertical", 0.0))
    horizontal = float(mouth.get("horizontal", 0.0))
    mar = float(mouth.get("mar", vertical / horizontal if horizontal else 0.0))
    cols = st.columns(4)
    cols[0].metric("Mouth opening", f"{vertical:.3f}")
    cols[1].metric("Mouth width", f"{horizontal:.3f}")
    cols[2].metric("MAR", f"{mar:.3f}")
    cols[3].metric("Vision Hz", f"{rate:.1f}")


def _append_rolling(key: str, value: float, limit: int = 120) -> None:
    values = st.session_state.setdefault(key, [])
    values.append(value)
    if len(values) > limit:
        del values[:-limit]


def _status_badge(label: str, state: str) -> str:
    normalized = state.lower()
    if normalized in {"connected", "healthy", "recording", "results_ready", "done"}:
        color = "#167a3a"
        background = "#e8f5ee"
    elif normalized in {"waiting", "idle", "processing", "stopped", "pending"}:
        color = "#8a5a00"
        background = "#fff4db"
    else:
        color = "#9b1c1c"
        background = "#fdecec"
    return (
        f"<span style='display:inline-block;padding:0.45rem 0.7rem;"
        f"border-radius:999px;background:{background};color:{color};"
        f"font-weight:700'>{label}: {state}</span>"
    )


def _exercise_name(exercise: dict[str, Any]) -> str:
    properties = exercise.get("properties")
    if isinstance(properties, dict):
        for key in ("name", "condition", "exercise", "label"):
            value = properties.get(key)
            if value:
                return str(value)
    return str(exercise.get("id", "n/a"))[:8]


if __name__ == "__main__":
    from frontend.standalone import run_page

    run_page(render, "Live Experiment")
