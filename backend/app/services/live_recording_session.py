"""Single-Pi live recording session manager."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import time
from threading import RLock
from typing import Any, Literal

from backend.app.integrations.raw_frames import RawExerciseFrames


FrameType = Literal["imu", "audio", "camera", "mouth"]
RecordingState = Literal["idle", "recording", "processing", "results_ready", "error"]


@dataclass(slots=True)
class RecordingBuffers:
    """Buffered numeric frames for one active exercise recording."""

    imu: list[dict[str, Any]] = field(default_factory=list)
    audio: list[dict[str, Any]] = field(default_factory=list)
    mouth: list[dict[str, Any]] = field(default_factory=list)

    def to_raw_frames(self) -> RawExerciseFrames:
        """Return an immutable raw-frame payload for storage."""
        return RawExerciseFrames.from_sequences(
            imu=self.imu,
            audio=self.audio,
            mouth=self.mouth,
        )


class LiveRecordingSessionManager:
    """Track one connected Pi and one active recording session."""

    def __init__(self, preview_min_interval_seconds: float = 0.2) -> None:
        self._lock = RLock()
        self._preview_min_interval_seconds = preview_min_interval_seconds
        self._active_exercise_id: str | None = None
        self._state: RecordingState = "idle"
        self._recording_started_at: float | None = None
        self._pi_connected = False
        self._pi_connected_at: float | None = None
        self._latest: dict[str, Any] = {}
        self._frame_counts: dict[str, int] = {
            "imu": 0,
            "audio": 0,
            "camera": 0,
            "mouth": 0,
        }
        self._frame_times: dict[str, deque[float]] = {
            frame_type: deque(maxlen=180)
            for frame_type in ("imu", "audio", "camera", "mouth")
        }
        self._buffers = RecordingBuffers()
        self._last_camera_preview_at = 0.0
        self._last_error: str | None = None

    def reset(self) -> None:
        """Reset all mutable state for tests and application shutdown."""
        with self._lock:
            self.__init__(self._preview_min_interval_seconds)

    def mark_pi_connected(self) -> None:
        """Record that a Pi WebSocket client is connected."""
        with self._lock:
            self._pi_connected = True
            self._pi_connected_at = time.time()

    def mark_pi_disconnected(self) -> None:
        """Record that the Pi WebSocket client disconnected."""
        with self._lock:
            self._pi_connected = False

    def start_recording(self, exercise_id: str) -> None:
        """Activate one exercise and clear in-memory frame buffers."""
        with self._lock:
            self._active_exercise_id = exercise_id
            self._state = "recording"
            self._recording_started_at = time.time()
            self._buffers = RecordingBuffers()
            self._frame_counts = {key: 0 for key in self._frame_counts}
            for timestamps in self._frame_times.values():
                timestamps.clear()
            self._last_error = None

    def stop_recording(self, exercise_id: str) -> RawExerciseFrames:
        """Stop persistence and return buffered frames for the exercise."""
        with self._lock:
            if self._active_exercise_id != exercise_id:
                frames = RecordingBuffers().to_raw_frames()
            else:
                frames = self._buffers.to_raw_frames()
            self._active_exercise_id = None
            self._state = "processing"
            self._recording_started_at = None
            self._buffers = RecordingBuffers()
            return frames

    def mark_results_ready(self) -> None:
        """Mark the last stopped recording as processed."""
        with self._lock:
            self._state = "results_ready"
            self._last_error = None

    def mark_error(self, message: str) -> None:
        """Mark processing or capture failure without dropping raw data."""
        with self._lock:
            self._state = "error"
            self._last_error = message

    def receive_frame(self, frame: dict[str, Any]) -> None:
        """Record a Pi frame for preview and, when active, persistence."""
        frame_type = frame.get("type")
        if frame_type not in {"imu", "audio", "camera", "mouth"}:
            return

        now = time.time()
        with self._lock:
            self._frame_counts[frame_type] += 1
            self._frame_times[frame_type].append(now)
            normalized = self._normalize_frame(frame)
            if normalized is not None and frame_type != "camera":
                self._latest[frame_type] = normalized
            elif (
                normalized is not None
                and frame_type == "camera"
                and now - self._last_camera_preview_at >= self._preview_min_interval_seconds
            ):
                self._latest["camera"] = normalized
                self._last_camera_preview_at = now
            if self._state != "recording":
                return
            if frame_type == "imu" and normalized is not None:
                self._buffers.imu.append(normalized)
            elif frame_type == "audio" and normalized is not None:
                self._buffers.audio.append(normalized)
            elif frame_type == "mouth" and normalized is not None:
                self._buffers.mouth.append(normalized)

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-compatible live-state snapshot."""
        with self._lock:
            elapsed = (
                time.time() - self._recording_started_at
                if self._recording_started_at is not None
                else 0.0
            )
            return {
                "piConnected": self._pi_connected,
                "piConnectedAt": self._pi_connected_at,
                "recordingState": self._state,
                "activeExerciseId": self._active_exercise_id,
                "elapsedRecordingSeconds": elapsed,
                "latest": dict(self._latest),
                "frameCounts": dict(self._frame_counts),
                "frameRates": {
                    frame_type: self._estimate_rate(timestamps)
                    for frame_type, timestamps in self._frame_times.items()
                },
                "lastError": self._last_error,
            }

    def _normalize_frame(self, frame: dict[str, Any]) -> dict[str, Any] | None:
        frame_type = frame["type"]
        try:
            if frame_type == "imu":
                return {
                    "ts": float(frame["ts"]),
                    "accel_x": int(frame["accel_x"]),
                    "accel_y": int(frame["accel_y"]),
                    "accel_z": int(frame["accel_z"]),
                    "gyro_x": int(frame["gyro_x"]),
                    "gyro_y": int(frame["gyro_y"]),
                    "gyro_z": int(frame["gyro_z"]),
                }
            if frame_type == "audio":
                return {"ts": float(frame["ts"]), "spl": float(frame["spl"])}
            if frame_type == "mouth":
                return {
                    "ts": float(frame["ts"]),
                    "vertical": float(frame["vertical"]),
                    "horizontal": float(frame["horizontal"]),
                    **(
                        {"mar": float(frame["mar"])}
                        if "mar" in frame
                        else {}
                    ),
                }
            if frame_type == "camera":
                jpeg = frame.get("jpeg")
                if not isinstance(jpeg, str):
                    return None
                return {"ts": float(frame["ts"]), "jpeg": jpeg}
        except (KeyError, TypeError, ValueError):
            return None
        return None

    @staticmethod
    def _estimate_rate(timestamps: deque[float]) -> float:
        if len(timestamps) < 2:
            return 0.0
        duration = timestamps[-1] - timestamps[0]
        if duration <= 0.0:
            return 0.0
        return (len(timestamps) - 1) / duration


live_recording_manager = LiveRecordingSessionManager()
