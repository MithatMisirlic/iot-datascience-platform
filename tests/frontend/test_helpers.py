"""Tests for pure frontend helper functions."""

from __future__ import annotations

import pytest

from frontend.components.charts import (
    prepare_completeness_dataframe,
    prepare_mouth_opening_dataframe,
    prepare_signal_dataframe,
    series_summary,
)
from frontend.components.forms import (
    compact_payload,
    parse_optional_float,
    parse_optional_int,
    parse_properties_json,
)
from frontend.components.results import (
    build_research_summary_markdown,
    normalize_exercise_data,
    normalize_signal,
)
from frontend.state import (
    reset_exercise_selection_if_invalid,
    reset_experiment_selection_if_invalid,
)


def test_results_normalization_handles_missing_and_empty_fields() -> None:
    """Optional missing result sections normalize to empty chartable data."""

    normalized = normalize_exercise_data({"exerciseId": "ex-1"})

    assert normalized["exerciseId"] == "ex-1"
    assert normalized["mouthOpening"] == {"values": [], "sampleRate": 0.0}
    assert normalized["soundPressure"] == {"values": [], "sampleRate": 0.0}
    assert normalized["footSpeed"] == {"values": [], "sampleRate": 0.0}
    assert normalized["aggregates"]["averages"] == {}
    assert normalized["aggregates"]["stepLengths"] == {"values": [], "sampleRate": 0.0}
    assert normalized["metadata"] == {}


def test_results_normalization_preserves_analysis_metadata() -> None:
    """Extended analysis metadata remains available for dashboard rendering."""

    payload = {
        "metadata": {
            "analysis": {
                "audio": {"syllable_count": 3},
                "movement": {"step_count": 4},
                "vision": {"mar_mean": 0.2},
                "overall": {"processing_duration_seconds": 0.0},
            }
        }
    }

    assert normalize_exercise_data(payload)["metadata"] == payload["metadata"]


def test_signal_normalization_preserves_unit_and_values() -> None:
    """Signal sections keep usable values, sample rate, and unit."""

    assert normalize_signal({"values": [1, 2], "sampleRate": "60", "unit": "Pa"}) == {
        "values": [1, 2],
        "sampleRate": 60.0,
        "unit": "Pa",
    }


def test_chart_data_preparation_filters_invalid_samples() -> None:
    """Chart helpers return deterministic dataframes for mixed data."""

    signal = prepare_signal_dataframe([1, "2.5", None, "bad"], "value")
    assert signal.to_dict("records") == [
        {"sample": 0, "value": 1.0},
        {"sample": 1, "value": 2.5},
    ]

    mouth = prepare_mouth_opening_dataframe([[1, 2], ["3", "4.5"], [5], "bad"])
    assert mouth.to_dict("records") == [
        {"sample": 0, "vertical": 1.0, "horizontal": 2.0},
        {"sample": 1, "vertical": 3.0, "horizontal": 4.5},
    ]


def test_series_summary_handles_empty_and_numbers() -> None:
    """Summary helpers avoid crashes on empty optional series."""

    assert series_summary([]) == {"count": 0, "min": None, "max": None, "mean": None}
    assert series_summary([1, 2, "bad", 3]) == {
        "count": 3,
        "min": 1.0,
        "max": 3.0,
        "mean": 2.0,
    }


def test_completeness_chart_preparation_filters_invalid_values() -> None:
    """Completeness chart data remains deterministic for mixed metadata."""

    dataframe = prepare_completeness_dataframe(
        {"imu": 1.0, "audio": "0.5", "vision": None, "bad": "n/a"}
    )

    assert dataframe.to_dict("records") == [
        {"modality": "imu", "completeness": 1.0},
        {"modality": "audio", "completeness": 0.5},
    ]


def test_research_summary_is_descriptive_and_non_diagnostic() -> None:
    """Research summary export contains available fields and a limitation."""

    summary = build_research_summary_markdown(
        {
            "exerciseId": "ex-1",
            "startedAt": "2026-01-01T00:00:00+00:00",
            "endedAt": "2026-01-01T00:00:02+00:00",
            "soundPressure": {"values": [1.0, 2.0], "sampleRate": 60.0},
            "footSpeed": {"values": [0.1], "sampleRate": 60.0},
            "mouthOpening": {"values": [[1.0, 2.0]], "sampleRate": 5.0},
            "aggregates": {},
        }
    )

    assert "Exercise ID: ex-1" in summary
    assert "Duration: 2.0s" in summary
    assert "not a medical diagnostic output" in summary
    assert "No Parkinson's disease classification" in summary


def test_form_parsers_and_payload_compaction() -> None:
    """Pure form helpers validate user-entered optional values."""

    assert parse_properties_json('{"condition": "average_steps"}') == {
        "condition": "average_steps"
    }
    assert parse_optional_int("63", "Age") == 63
    assert parse_optional_float("78.5", "Weight") == 78.5
    assert compact_payload({"patientNumber": "P-1", "age": None, "height": ""}) == {
        "patientNumber": "P-1"
    }

    with pytest.raises(ValueError):
        parse_properties_json('{"bad": 1}')
    with pytest.raises(ValueError):
        parse_optional_int("not-int", "Age")
    with pytest.raises(ValueError):
        parse_optional_float("not-float", "Height")


def test_selection_helpers_reset_invalid_state() -> None:
    """Deleted parent and child selections are cleared safely."""

    state = {"selected_experiment_id": "exp-old", "selected_exercise_id": "ex-old"}
    reset_experiment_selection_if_invalid(state, {"exp-new"})
    assert state == {"selected_experiment_id": None, "selected_exercise_id": None}

    state = {"selected_experiment_id": "exp-1", "selected_exercise_id": "ex-old"}
    reset_exercise_selection_if_invalid(state, {"ex-new"})
    assert state == {"selected_experiment_id": "exp-1", "selected_exercise_id": None}
