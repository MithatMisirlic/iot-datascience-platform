"""Reusable backend test data factories."""

from typing import Any


def processed_features() -> dict[str, Any]:
    """Return complete fake processor output matching ExerciseData fields."""

    return {
        "mouthOpening": {
            "values": [[0.1, 0.2], [0.2, 0.3]],
            "sampleRate": 30,
        },
        "soundPressure": {
            "values": [0.01, 0.02],
            "sampleRate": 48000,
            "unit": "Pa",
        },
        "footSpeed": {
            "values": [12.5, 13.0],
            "sampleRate": 100,
            "unit": "cm/s",
        },
        "aggregates": {
            "stepLengths": {"values": [42.0, 44.0], "unit": "cm"},
            "averages": {"footSpeed": 12.75, "stepLength": 43.0},
            "medians": {"footSpeed": 12.75, "stepLength": 43.0},
        },
    }
