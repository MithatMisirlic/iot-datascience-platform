"""Result normalization and rendering helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from frontend.components.charts import (
    prepare_completeness_dataframe,
    prepare_mouth_opening_dataframe,
    prepare_signal_dataframe,
    render_bar_chart,
    render_line_chart,
    render_timeline,
    series_summary,
)


def normalize_signal(section: Any) -> dict[str, Any]:
    """Normalize a signal section into a predictable dictionary."""

    if not isinstance(section, Mapping):
        return {"values": [], "sampleRate": 0.0}
    values = section.get("values")
    if not isinstance(values, list):
        values = []
    sample_rate = section.get("sampleRate", 0.0)
    try:
        sample_rate = float(sample_rate)
    except (TypeError, ValueError):
        sample_rate = 0.0
    normalized: dict[str, Any] = {
        "values": values,
        "sampleRate": sample_rate,
    }
    if isinstance(section.get("unit"), str):
        normalized["unit"] = section["unit"]
    return normalized


def normalize_exercise_data(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Normalize ExerciseData so UI code can handle missing optional fields."""

    source: Mapping[str, Any] = payload or {}
    aggregates = source.get("aggregates")
    if not isinstance(aggregates, Mapping):
        aggregates = {}
    return {
        "exerciseId": source.get("exerciseId"),
        "startedAt": source.get("startedAt"),
        "endedAt": source.get("endedAt"),
        "mouthOpening": normalize_signal(source.get("mouthOpening")),
        "soundPressure": normalize_signal(source.get("soundPressure")),
        "footSpeed": normalize_signal(source.get("footSpeed")),
        "aggregates": {
            "stepLengths": normalize_signal(aggregates.get("stepLengths")),
            "averages": _normalize_stats(aggregates.get("averages")),
            "medians": _normalize_stats(aggregates.get("medians")),
        },
        "metadata": source.get("metadata") if isinstance(source.get("metadata"), Mapping) else {},
    }


def _normalize_stats(value: Any) -> dict[str, float]:
    if not isinstance(value, Mapping):
        return {}
    stats: dict[str, float] = {}
    for key, raw in value.items():
        try:
            stats[str(key)] = float(raw)
        except (TypeError, ValueError):
            continue
    return stats


def render_exercise_results(payload: Mapping[str, Any]) -> None:
    """Render ExerciseData without treating values as diagnostic outputs."""

    import json
    import streamlit as st

    data = normalize_exercise_data(payload)
    st.caption(
        "Results are research feature outputs only. Foot speed is currently an "
        "acceleration-derived placeholder, not a validated physical speed or "
        "medical diagnosis."
    )

    _render_result_header(data)
    speech_tab, movement_tab, vision_tab, overall_tab = st.tabs(
        ["Speech", "Movement", "Vision", "Overall"]
    )
    with speech_tab:
        _render_speech(data)
    with movement_tab:
        _render_movement(data)
    with vision_tab:
        _render_vision(data)
    with overall_tab:
        _render_overall(data)

    st.divider()
    st.subheader("Research Summary")
    summary = build_research_summary_markdown(data)
    st.markdown(summary)
    left, middle, right = st.columns(3)
    left.download_button(
        "Download ProcessedResult JSON",
        data=json.dumps(payload, indent=2, default=str),
        file_name=f"exercise-{data.get('exerciseId') or 'result'}.json",
        mime="application/json",
    )
    middle.download_button(
        "Download Research Summary",
        data=summary,
        file_name=f"exercise-{data.get('exerciseId') or 'summary'}.md",
        mime="text/markdown",
    )
    csv_data = _series_csv(data)
    right.download_button(
        "Download Series CSV",
        data=csv_data,
        file_name=f"exercise-{data.get('exerciseId') or 'series'}.csv",
        mime="text/csv",
        disabled=not csv_data.strip(),
    )


def render_analysis_metadata(metadata: Mapping[str, Any]) -> None:
    """Render extended pipeline analysis if present in the payload."""

    import pandas as pd
    import streamlit as st

    report = metadata.get("analysis") if isinstance(metadata, Mapping) else None
    if not isinstance(report, Mapping):
        st.info("Extended analysis metadata is not exposed by this API response.")
        return

    st.divider()
    st.subheader("Extended Analysis")

    audio = report.get("audio") if isinstance(report.get("audio"), Mapping) else {}
    movement = report.get("movement") if isinstance(report.get("movement"), Mapping) else {}
    vision = report.get("vision") if isinstance(report.get("vision"), Mapping) else {}
    overall = report.get("overall") if isinstance(report.get("overall"), Mapping) else {}

    st.markdown("#### Audio")
    cols = st.columns(3)
    cols[0].metric("Syllables", _metric_value(audio.get("syllable_count")))
    cols[1].metric("Clarity proxy", _metric_value(audio.get("speech_clarity_proxy")))
    cols[2].metric("ZCR mean", _metric_value(audio.get("zero_crossing_rate_mean")))
    mfcc_means = audio.get("mfcc_means")
    mfcc_stds = audio.get("mfcc_stds")
    if isinstance(mfcc_means, list):
        std_values = mfcc_stds if isinstance(mfcc_stds, list) else []
        if len(std_values) != len(mfcc_means):
            std_values = [None for _ in mfcc_means]
        st.dataframe(
            pd.DataFrame(
                {
                    "coefficient": list(range(1, len(mfcc_means) + 1)),
                    "mean": mfcc_means,
                    "std": std_values,
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("#### Movement")
    cols = st.columns(3)
    cols[0].metric("Steps", _metric_value(movement.get("step_count")))
    cols[1].metric("Cadence", _metric_value(movement.get("cadence_steps_per_minute")))
    cols[2].metric("Tremor frequency Hz", _metric_value(movement.get("dominant_frequency_hz")))

    st.markdown("#### Vision")
    cols = st.columns(3)
    cols[0].metric("MAR mean", _metric_value(vision.get("mar_mean")))
    cols[1].metric("Jaw amplitude", _metric_value(vision.get("jaw_movement_amplitude")))
    cols[2].metric("Jaw speed", _metric_value(vision.get("average_jaw_speed")))

    st.markdown("#### Overall")
    cols = st.columns(3)
    cols[0].metric("Duration", _metric_value(overall.get("experiment_duration")))
    cols[1].metric("Processing seconds", _metric_value(overall.get("processing_duration_seconds")))
    completeness = overall.get("completeness")
    if isinstance(completeness, Mapping):
        cols[2].metric("Complete modalities", f"{sum(float(v) > 0 for v in completeness.values())}/3")
        st.dataframe(
            pd.DataFrame(
                [{"modality": key, "completeness": value} for key, value in completeness.items()]
            ),
            use_container_width=True,
            hide_index=True,
        )
    cross_modal = overall.get("cross_modal")
    if isinstance(cross_modal, Mapping):
        st.dataframe(
            pd.DataFrame(
                [{"metric": key, "value": value} for key, value in cross_modal.items()]
            ),
            use_container_width=True,
            hide_index=True,
        )


def _metric_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    if value is None:
        return "n/a"
    return str(value)


def _render_result_header(data: Mapping[str, Any]) -> None:
    import streamlit as st

    mouth = data["mouthOpening"]
    sound = data["soundPressure"]
    foot = data["footSpeed"]
    duration = _duration_seconds(data.get("startedAt"), data.get("endedAt"))
    cols = st.columns(4)
    cols[0].metric("Experiment duration", _format_seconds(duration))
    cols[1].metric("Mouth frames", len(mouth["values"]))
    cols[2].metric("Audio frames", len(sound["values"]))
    cols[3].metric("Movement frames", len(foot["values"]))
    with st.expander("Timing and identifiers", expanded=False):
        st.write({"exerciseId": data.get("exerciseId"), "startedAt": data.get("startedAt"), "endedAt": data.get("endedAt")})


def _render_speech(data: Mapping[str, Any]) -> None:
    import pandas as pd
    import streamlit as st

    sound = data["soundPressure"]
    analysis = _analysis_section(data, "audio")
    summary = series_summary(sound["values"])
    cols = st.columns(4)
    cols[0].metric("Average SPL/RMS", _metric_value(summary["mean"]))
    cols[1].metric("Speech clarity", _metric_value(analysis.get("speech_clarity_proxy")))
    cols[2].metric("Syllables", _metric_value(analysis.get("syllable_count")))
    cols[3].metric("Syllables/sec", _metric_value(analysis.get("syllables_per_second")))
    render_line_chart(
        prepare_signal_dataframe(sound["values"], "sound pressure"),
        f"Rolling SPL/RMS ({sound.get('unit', 'unitless')})",
    )
    mfcc_means = analysis.get("mfcc_means")
    mfcc_stds = analysis.get("mfcc_stds")
    if isinstance(mfcc_means, list):
        st.subheader("MFCC Summary")
        std_values = mfcc_stds if isinstance(mfcc_stds, list) else []
        if len(std_values) != len(mfcc_means):
            std_values = [None for _ in mfcc_means]
        st.dataframe(
            pd.DataFrame(
                {
                    "coefficient": list(range(1, len(mfcc_means) + 1)),
                    "mean": mfcc_means,
                    "std": std_values,
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("MFCC metadata is not available in this API response.")


def _render_movement(data: Mapping[str, Any]) -> None:
    import streamlit as st

    foot = data["footSpeed"]
    analysis = _analysis_section(data, "movement")
    summary = series_summary(foot["values"])
    cols = st.columns(4)
    cols[0].metric("Step count", _metric_value(analysis.get("step_count")))
    cols[1].metric("Cadence", _metric_value(analysis.get("cadence_steps_per_minute")))
    cols[2].metric("Dominant frequency", _metric_value(analysis.get("dominant_frequency_hz")))
    cols[3].metric("Foot proxy mean", _metric_value(summary["mean"]))
    render_line_chart(
        prepare_signal_dataframe(foot["values"], "acceleration-derived proxy"),
        f"Foot Speed Placeholder ({foot.get('unit', 'unitless')})",
    )
    step_lengths = data["aggregates"]["stepLengths"]
    render_line_chart(
        prepare_signal_dataframe(step_lengths["values"], "step length"),
        f"Step Lengths ({step_lengths.get('unit', 'unitless')})",
    )
    st.caption("Step markers are shown when the processing metadata exposes detected step events.")
    step_markers = analysis.get("step_markers")
    if isinstance(step_markers, list) and step_markers:
        render_bar_chart(
            prepare_signal_dataframe(step_markers, "step marker"),
            "Step Detection Markers",
            "sample",
            "step marker",
        )


def _render_vision(data: Mapping[str, Any]) -> None:
    import streamlit as st

    mouth = data["mouthOpening"]
    analysis = _analysis_section(data, "vision")
    averages = data["aggregates"]["averages"]
    cols = st.columns(4)
    cols[0].metric("Mouth opening", _metric_value(averages.get("mouthOpeningVertical")))
    cols[1].metric("MAR", _metric_value(analysis.get("mar_mean")))
    cols[2].metric("Jaw amplitude", _metric_value(analysis.get("jaw_movement_amplitude")))
    cols[3].metric("Jaw speed", _metric_value(analysis.get("average_jaw_speed")))
    mouth_df = prepare_mouth_opening_dataframe(mouth["values"])
    render_line_chart(mouth_df, "Mouth Opening Timeline")
    if not mouth_df.empty:
        mar_df = mouth_df.copy()
        mar_df["MAR"] = mar_df.apply(
            lambda row: row["vertical"] / row["horizontal"] if row["horizontal"] else 0.0,
            axis=1,
        )
        render_line_chart(mar_df[["sample", "MAR"]], "MAR Timeline")


def _render_overall(data: Mapping[str, Any]) -> None:
    import pandas as pd
    import streamlit as st

    overall = _analysis_section(data, "overall")
    duration = _duration_seconds(data.get("startedAt"), data.get("endedAt"))
    completeness = overall.get("completeness") if isinstance(overall.get("completeness"), Mapping) else {}
    sample_rates = overall.get("sensor_sample_rates") if isinstance(overall.get("sensor_sample_rates"), Mapping) else {}
    timestamps = overall.get("first_timestamps") if isinstance(overall.get("first_timestamps"), Mapping) else {}
    cols = st.columns(4)
    cols[0].metric("Duration", _format_seconds(duration))
    cols[1].metric("Processing duration", _metric_value(overall.get("processing_duration_seconds")))
    cols[2].metric("Complete modalities", _complete_modality_count(completeness))
    cols[3].metric("Sample-rate entries", len(sample_rates))
    render_bar_chart(
        prepare_completeness_dataframe(dict(completeness)),
        "Completeness by Modality",
        "modality",
        "completeness",
    )
    render_timeline(dict(timestamps), "Synchronization Timeline")
    if sample_rates:
        st.subheader("Sensor Sample Rates")
        st.dataframe(
            pd.DataFrame(
                [{"sensor": key, "sampleRateHz": value} for key, value in sample_rates.items()]
            ),
            use_container_width=True,
            hide_index=True,
        )
    _render_aggregate_table(data)


def _render_aggregate_table(data: Mapping[str, Any]) -> None:
    import pandas as pd
    import streamlit as st

    averages = data["aggregates"]["averages"]
    medians = data["aggregates"]["medians"]
    st.subheader("Aggregate Statistics")
    if averages or medians:
        st.dataframe(
            pd.DataFrame(
                [
                    {"statistic": "average", **averages},
                    {"statistic": "median", **medians},
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
        return
    st.info("No aggregate statistics are available.")


def build_research_summary_markdown(payload: Mapping[str, Any]) -> str:
    """Build a descriptive, non-diagnostic markdown report."""

    data = normalize_exercise_data(payload)
    mouth = data["mouthOpening"]
    sound = data["soundPressure"]
    foot = data["footSpeed"]
    audio = _analysis_section(data, "audio")
    movement = _analysis_section(data, "movement")
    vision = _analysis_section(data, "vision")
    overall = _analysis_section(data, "overall")
    duration = _duration_seconds(data.get("startedAt"), data.get("endedAt"))
    return "\n".join(
        [
            "# Research Summary",
            "",
            "This report contains descriptive research features only. It is not a medical diagnostic output.",
            "",
            "## Experiment Summary",
            f"- Exercise ID: {data.get('exerciseId') or 'n/a'}",
            f"- Duration: {_format_seconds(duration)}",
            f"- Started: {data.get('startedAt') or 'n/a'}",
            f"- Ended: {data.get('endedAt') or 'n/a'}",
            "",
            "## Connected Sensors and Frames",
            f"- Audio frames: {len(sound['values'])}",
            f"- Movement proxy frames: {len(foot['values'])}",
            f"- Mouth/vision frames: {len(mouth['values'])}",
            "",
            "## Speech Analysis",
            f"- Average SPL/RMS: {_metric_value(series_summary(sound['values'])['mean'])}",
            f"- Speech clarity proxy: {_metric_value(audio.get('speech_clarity_proxy'))}",
            f"- Syllable count: {_metric_value(audio.get('syllable_count'))}",
            "",
            "## Movement Analysis",
            f"- Step count: {_metric_value(movement.get('step_count'))}",
            f"- Cadence: {_metric_value(movement.get('cadence_steps_per_minute'))}",
            f"- Dominant frequency: {_metric_value(movement.get('dominant_frequency_hz'))}",
            "",
            "## Vision Analysis",
            f"- MAR mean: {_metric_value(vision.get('mar_mean'))}",
            f"- Jaw movement amplitude: {_metric_value(vision.get('jaw_movement_amplitude'))}",
            "",
            "## Overall Observations",
            f"- Processing duration seconds: {_metric_value(overall.get('processing_duration_seconds'))}",
            f"- Complete modalities: {_complete_modality_count(overall.get('completeness') if isinstance(overall.get('completeness'), Mapping) else {})}",
            "",
            "## Limitations",
            "- Camera frames are used for live preview and are not stored in SQLite.",
            "- Foot speed is an acceleration-derived research placeholder.",
            "- No Parkinson's disease classification or diagnosis is performed.",
        ]
    )


def _series_csv(data: Mapping[str, Any]) -> str:
    import pandas as pd

    rows: list[dict[str, Any]] = []
    for name, values in (
        ("soundPressure", data["soundPressure"]["values"]),
        ("footSpeed", data["footSpeed"]["values"]),
    ):
        for index, value in enumerate(values):
            rows.append({"signal": name, "sample": index, "value": value})
    for index, value in enumerate(data["mouthOpening"]["values"]):
        if isinstance(value, list | tuple) and len(value) >= 2:
            rows.append({"signal": "mouthVertical", "sample": index, "value": value[0]})
            rows.append({"signal": "mouthHorizontal", "sample": index, "value": value[1]})
    if not rows:
        return ""
    return pd.DataFrame(rows).to_csv(index=False)


def _analysis_section(data: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    metadata = data.get("metadata")
    analysis = metadata.get("analysis") if isinstance(metadata, Mapping) else None
    section = analysis.get(key) if isinstance(analysis, Mapping) else None
    return section if isinstance(section, Mapping) else {}


def _duration_seconds(started: Any, ended: Any) -> float | None:
    from datetime import datetime

    if not isinstance(started, str) or not isinstance(ended, str):
        return None
    try:
        start = datetime.fromisoformat(started.replace("Z", "+00:00"))
        end = datetime.fromisoformat(ended.replace("Z", "+00:00"))
    except ValueError:
        return None
    return max((end - start).total_seconds(), 0.0)


def _format_seconds(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}s"


def _complete_modality_count(completeness: Mapping[str, Any]) -> str:
    if not completeness:
        return "0/0"
    complete = sum(float(value or 0) > 0 for value in completeness.values())
    return f"{complete}/{len(completeness)}"
