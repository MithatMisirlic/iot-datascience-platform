"""Mouth-opening and mouth-aspect-ratio feature extraction."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from pipeline.core.statistics import (
    duration_seconds,
    maximum,
    mean,
    minimum,
    sample_rate_estimate_hz,
)


@dataclass(frozen=True, slots=True)
class MouthFeatures:
    """Generic summary features derived from mouth geometry samples."""

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

    def to_dict(self) -> dict[str, float | int]:
        """Return a JSON-compatible representation."""
        return asdict(self)


def mouth_aspect_ratios(frames: Sequence[Mapping[str, Any]]) -> list[float]:
    """Return vertical/horizontal ratios, using zero for zero-width samples."""
    ratios: list[float] = []
    for frame in frames:
        vertical = float(frame["vertical"])
        horizontal = float(frame["horizontal"])
        ratios.append(vertical / horizontal if horizontal != 0.0 else 0.0)
    return ratios


def process_mouth_frames(frames: Sequence[Mapping[str, Any]]) -> MouthFeatures:
    """Extract deterministic mouth geometry and MAR features."""
    timestamps = [float(frame["ts"]) for frame in frames]
    vertical_values = [float(frame["vertical"]) for frame in frames]
    horizontal_values = [float(frame["horizontal"]) for frame in frames]
    mar_values = mouth_aspect_ratios(frames)

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
        sample_count=len(frames),
        sample_rate_estimate_hz=sample_rate_estimate_hz(timestamps),
    )
