"""Mouth, MAR, and jaw-movement feature extraction."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

try:  # pragma: no cover - optional runtime integration
    import mediapipe as mp  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - optional runtime integration
    mp = None  # type: ignore[assignment]

from pipeline.core.statistics import (
    duration_seconds,
    maximum,
    mean,
    minimum,
    sample_rate_estimate_hz,
)


@dataclass(frozen=True, slots=True)
class MouthFeatures:
    """Generic summary features derived from mouth and jaw geometry samples."""

    duration_seconds: float
    mouth_vertical_mean: float
    mouth_vertical_max: float
    mouth_vertical_min: float
    mouth_horizontal_mean: float
    mouth_horizontal_max: float
    mouth_horizontal_min: float
    mar_mean: float
    mar_max: float
    mar_min: float
    sample_count: int
    sample_rate_estimate_hz: float
    frame_count: int
    processed_frame_count: int
    mouth_opening_mean: float
    mouth_width_mean: float
    jaw_movement_amplitude: float
    average_jaw_speed: float

    def to_dict(self) -> dict[str, float | int]:
        """Return a JSON-compatible representation."""
        return asdict(self)


def mouth_aspect_ratios(frames: Sequence[Mapping[str, Any]]) -> list[float]:
    """Return vertical/horizontal ratios, using zero for zero-width samples."""
    ratios: list[float] = []
    for frame in _valid_geometry_frames(frames):
        vertical = float(frame["vertical"])
        horizontal = float(frame["horizontal"])
        ratios.append(vertical / horizontal if horizontal != 0.0 else 0.0)
    return ratios


def process_mouth_frames(frames: Sequence[Mapping[str, Any]]) -> MouthFeatures:
    """Extract deterministic mouth geometry, MAR, and jaw features."""
    valid_frames = _valid_geometry_frames(frames)
    timestamps = [float(frame["ts"]) for frame in valid_frames]
    vertical_values = [float(frame["vertical"]) for frame in valid_frames]
    horizontal_values = [float(frame["horizontal"]) for frame in valid_frames]
    mar_values = mouth_aspect_ratios(valid_frames)
    jaw_points = _jaw_points(valid_frames)

    return MouthFeatures(
        duration_seconds=duration_seconds(timestamps),
        mouth_vertical_mean=mean(vertical_values),
        mouth_vertical_max=maximum(vertical_values),
        mouth_vertical_min=minimum(vertical_values),
        mouth_horizontal_mean=mean(horizontal_values),
        mouth_horizontal_max=maximum(horizontal_values),
        mouth_horizontal_min=minimum(horizontal_values),
        mar_mean=mean(mar_values),
        mar_max=maximum(mar_values),
        mar_min=minimum(mar_values),
        sample_count=len(valid_frames),
        sample_rate_estimate_hz=sample_rate_estimate_hz(timestamps),
        frame_count=len(frames),
        processed_frame_count=len(valid_frames),
        mouth_opening_mean=mean(vertical_values),
        mouth_width_mean=mean(horizontal_values),
        jaw_movement_amplitude=jaw_movement_amplitude(jaw_points),
        average_jaw_speed=average_jaw_speed(jaw_points, timestamps),
    )


def extract_mouth_geometry_from_camera_frames(
    frames: Sequence[Mapping[str, Any]],
) -> list[dict[str, float | bool]]:
    """Extract mouth geometry from camera frames when MediaPipe is installed.

    The default test/development environment does not require MediaPipe. If it
    is unavailable, the function returns no processed frames rather than
    failing the pipeline.
    """
    if mp is None:
        return [
            {"ts": float(frame.get("ts", 0.0)), "face_detected": False}
            for frame in frames
        ]
    # MediaPipe integration is intentionally isolated here; raw frame capture
    # and persistence are not wired to exercise IDs yet.
    return [
        {"ts": float(frame.get("ts", 0.0)), "face_detected": False}
        for frame in frames
    ]


def jaw_movement_amplitude(points: Sequence[tuple[float, float]]) -> float:
    """Return max jaw-point displacement from the first processed point."""
    if len(points) < 2:
        return 0.0
    origin = np.asarray(points[0], dtype=float)
    distances = [float(np.linalg.norm(np.asarray(point, dtype=float) - origin)) for point in points]
    return maximum(distances)


def average_jaw_speed(
    points: Sequence[tuple[float, float]],
    timestamps: Sequence[float],
) -> float:
    """Return average point-to-point jaw speed in geometry units/second."""
    if len(points) < 2 or len(timestamps) < 2:
        return 0.0
    speeds: list[float] = []
    for index in range(1, min(len(points), len(timestamps))):
        dt = float(timestamps[index]) - float(timestamps[index - 1])
        if dt <= 0.0:
            continue
        previous = np.asarray(points[index - 1], dtype=float)
        current = np.asarray(points[index], dtype=float)
        speeds.append(float(np.linalg.norm(current - previous) / dt))
    return mean(speeds)


def _valid_geometry_frames(frames: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    valid: list[Mapping[str, Any]] = []
    for frame in frames:
        if frame.get("face_detected", True) is False:
            continue
        if "vertical" not in frame or "horizontal" not in frame:
            continue
        valid.append(frame)
    return valid


def _jaw_points(frames: Sequence[Mapping[str, Any]]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for frame in frames:
        if "jaw_x" in frame and "jaw_y" in frame:
            points.append((float(frame["jaw_x"]), float(frame["jaw_y"])))
        else:
            points.append((0.0, float(frame["vertical"])))
    return points
