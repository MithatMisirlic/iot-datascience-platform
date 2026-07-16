"""Background WebSocket client for backend live-state updates."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
import json
from threading import Event, Lock, Thread
from typing import Any
from urllib.parse import urlparse

import websockets


def websocket_url_from_api_base(api_base_url: str) -> str:
    """Convert an HTTP API base URL to the backend `/ws` WebSocket URL."""
    parsed = urlparse(api_base_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    netloc = parsed.netloc or parsed.path
    return f"{scheme}://{netloc}/ws"


def normalize_live_state(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a defensive live-state shape for the dashboard."""
    source: Mapping[str, Any] = payload or {}
    latest = source.get("latest") if isinstance(source.get("latest"), Mapping) else {}
    return {
        "piConnected": bool(source.get("piConnected", False)),
        "recordingState": str(source.get("recordingState", "disconnected")),
        "activeExerciseId": source.get("activeExerciseId"),
        "elapsedRecordingSeconds": float(source.get("elapsedRecordingSeconds") or 0.0),
        "latest": dict(latest),
        "frameCounts": _mapping_of_numbers(source.get("frameCounts")),
        "frameRates": _mapping_of_numbers(source.get("frameRates")),
        "lastError": source.get("lastError"),
    }


class LiveStateClient:
    """Receive `/ws` state in a background thread for Streamlit reruns."""

    def __init__(self, websocket_url: str) -> None:
        self.websocket_url = websocket_url
        self._state = normalize_live_state(None)
        self._lock = Lock()
        self._stop = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        """Start the background receiver if it is not already running."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Ask the receiver to stop."""
        self._stop.set()

    def snapshot(self) -> dict[str, Any]:
        """Return the latest normalized state."""
        with self._lock:
            return dict(self._state)

    def _run(self) -> None:
        asyncio.run(self._receive_loop())

    async def _receive_loop(self) -> None:
        while not self._stop.is_set():
            try:
                async with websockets.connect(self.websocket_url) as websocket:
                    async for message in websocket:
                        if self._stop.is_set():
                            break
                        try:
                            payload = json.loads(message)
                        except json.JSONDecodeError:
                            continue
                        with self._lock:
                            self._state = normalize_live_state(payload)
            except Exception:
                with self._lock:
                    self._state = normalize_live_state(
                        {
                            "piConnected": False,
                            "recordingState": "disconnected",
                            "lastError": "Live-state WebSocket disconnected.",
                        }
                    )
                await asyncio.sleep(1.0)


def _mapping_of_numbers(value: Any) -> dict[str, float]:
    if not isinstance(value, Mapping):
        return {}
    output: dict[str, float] = {}
    for key, raw in value.items():
        try:
            output[str(key)] = float(raw)
        except (TypeError, ValueError):
            continue
    return output
