"""Pure session-state helpers used by Streamlit pages and tests."""

from __future__ import annotations

from typing import Any, MutableMapping


def reset_exercise_selection_if_invalid(
    state: MutableMapping[str, Any],
    valid_exercise_ids: set[str],
) -> None:
    """Clear selected exercise state after parent or exercise deletion."""

    selected = state.get("selected_exercise_id")
    if selected is not None and selected not in valid_exercise_ids:
        state["selected_exercise_id"] = None


def reset_experiment_selection_if_invalid(
    state: MutableMapping[str, Any],
    valid_experiment_ids: set[str],
) -> None:
    """Clear selected experiment and child exercise state after deletion."""

    selected = state.get("selected_experiment_id")
    if selected is not None and selected not in valid_experiment_ids:
        state["selected_experiment_id"] = None
        state["selected_exercise_id"] = None
