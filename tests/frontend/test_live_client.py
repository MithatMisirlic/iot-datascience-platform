"""Tests for live-state frontend helpers."""

from __future__ import annotations

import importlib

from frontend.live_client import normalize_live_state, websocket_url_from_api_base


def test_websocket_url_from_api_base() -> None:
    assert websocket_url_from_api_base("http://localhost:3000") == "ws://localhost:3000/ws"
    assert websocket_url_from_api_base("https://example.test/api") == "wss://example.test/ws"


def test_live_state_normalization_handles_missing_fields() -> None:
    normalized = normalize_live_state(None)

    assert normalized["piConnected"] is False
    assert normalized["recordingState"] == "disconnected"
    assert normalized["frameCounts"] == {}
    assert normalized["frameRates"] == {}


def test_live_state_normalization_preserves_numeric_values() -> None:
    normalized = normalize_live_state(
        {
            "piConnected": True,
            "recordingState": "recording",
            "activeExerciseId": "exercise-1",
            "elapsedRecordingSeconds": "1.5",
            "latest": {"audio": {"spl": 0.2}},
            "frameCounts": {"audio": 3},
            "frameRates": {"audio": "59.5"},
        }
    )

    assert normalized["piConnected"] is True
    assert normalized["activeExerciseId"] == "exercise-1"
    assert normalized["elapsedRecordingSeconds"] == 1.5
    assert normalized["latest"] == {"audio": {"spl": 0.2}}
    assert normalized["frameCounts"] == {"audio": 3.0}
    assert normalized["frameRates"] == {"audio": 59.5}


def test_live_experiment_page_imports() -> None:
    module = importlib.import_module("frontend.pages.live_experiment")

    assert callable(module.render)
