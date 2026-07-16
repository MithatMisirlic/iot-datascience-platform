"""Reusable chart-data helpers for the Streamlit dashboard."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd

try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:  # pragma: no cover - exercised only when Plotly is absent.
    px = None
    go = None


def _coerce_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def prepare_signal_dataframe(
    values: Iterable[Any] | None,
    value_label: str,
) -> pd.DataFrame:
    """Return sample-indexed scalar signal data safe for charting."""

    rows: list[dict[str, float | int]] = []
    for index, value in enumerate(values or []):
        number = _coerce_float(value)
        if number is not None:
            rows.append({"sample": index, value_label: number})
    return pd.DataFrame(rows)


def prepare_mouth_opening_dataframe(values: Iterable[Any] | None) -> pd.DataFrame:
    """Return sample-indexed mouth-opening pairs safe for charting."""

    rows: list[dict[str, float | int]] = []
    for index, sample in enumerate(values or []):
        if not isinstance(sample, (list, tuple)) or len(sample) < 2:
            continue
        vertical = _coerce_float(sample[0])
        horizontal = _coerce_float(sample[1])
        if vertical is None or horizontal is None:
            continue
        rows.append(
            {
                "sample": index,
                "vertical": vertical,
                "horizontal": horizontal,
            }
        )
    return pd.DataFrame(rows)


def prepare_magnitude_dataframe(
    values: Iterable[Any] | None,
    x_label: str,
    y_label: str,
) -> pd.DataFrame:
    """Return sample-indexed magnitude data from scalar values."""

    rows: list[dict[str, float | int]] = []
    for index, value in enumerate(values or []):
        number = _coerce_float(value)
        if number is not None:
            rows.append({"sample": index, x_label: index, y_label: number})
    return pd.DataFrame(rows)


def prepare_completeness_dataframe(completeness: dict[str, Any] | None) -> pd.DataFrame:
    """Return a tidy completeness table for charting."""

    rows: list[dict[str, float | str]] = []
    for modality, value in (completeness or {}).items():
        number = _coerce_float(value)
        if number is not None:
            rows.append({"modality": str(modality), "completeness": number})
    return pd.DataFrame(rows)


def series_summary(values: Iterable[Any] | None) -> dict[str, float | int | None]:
    """Compute non-diagnostic display statistics for a scalar series."""

    numbers = [
        number
        for number in (_coerce_float(value) for value in values or [])
        if number is not None
    ]
    if not numbers:
        return {"count": 0, "min": None, "max": None, "mean": None}
    return {
        "count": len(numbers),
        "min": min(numbers),
        "max": max(numbers),
        "mean": sum(numbers) / len(numbers),
    }


def render_line_chart(dataframe: pd.DataFrame, title: str) -> None:
    """Render a line chart with Plotly when available, otherwise Streamlit."""

    import streamlit as st

    st.subheader(title)
    if dataframe.empty:
        st.info("No chartable samples available.")
        return
    if px is not None:
        y_columns = [column for column in dataframe.columns if column != "sample"]
        figure = px.line(
            dataframe,
            x="sample",
            y=y_columns,
            markers=False,
            template="plotly_white",
        )
        figure.update_layout(
            margin={"l": 10, "r": 10, "t": 25, "b": 10},
            legend_title_text="",
            height=320,
        )
        st.plotly_chart(figure, use_container_width=True)
        return
    st.line_chart(dataframe.set_index("sample"))


def render_bar_chart(
    dataframe: pd.DataFrame,
    title: str,
    x: str,
    y: str,
) -> None:
    """Render a compact bar chart with a native fallback."""

    import streamlit as st

    st.subheader(title)
    if dataframe.empty:
        st.info("No chartable values available.")
        return
    if px is not None:
        figure = px.bar(
            dataframe,
            x=x,
            y=y,
            template="plotly_white",
            text_auto=".2f",
        )
        figure.update_layout(margin={"l": 10, "r": 10, "t": 25, "b": 10}, height=320)
        st.plotly_chart(figure, use_container_width=True)
        return
    st.bar_chart(dataframe.set_index(x)[y])


def render_timeline(
    timestamps: dict[str, Any],
    title: str,
) -> None:
    """Render synchronization timestamps as a simple timeline/table."""

    import streamlit as st

    rows = [
        {"modality": key, "timestamp": value}
        for key, value in timestamps.items()
        if value is not None
    ]
    st.subheader(title)
    if not rows:
        st.info("No synchronization timestamps are available.")
        return
    dataframe = pd.DataFrame(rows)
    if px is not None:
        figure = px.scatter(
            dataframe,
            x="timestamp",
            y="modality",
            template="plotly_white",
        )
        figure.update_traces(marker={"size": 12})
        figure.update_layout(margin={"l": 10, "r": 10, "t": 25, "b": 10}, height=260)
        st.plotly_chart(figure, use_container_width=True)
        return
    st.dataframe(dataframe, use_container_width=True, hide_index=True)
