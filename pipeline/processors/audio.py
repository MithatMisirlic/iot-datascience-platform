"""RMS audio-frame feature extraction."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from pipeline.core.statistics import (
    duration_seconds,
    maximum,
    mean,
    minimum,
    population_std,
    sample_rate_estimate_hz,
)


@dataclass(frozen=True, slots=True)
class AudioFeatures:
    """Generic summary features derived from RMS amplitude samples."""

    duration_seconds: float
    rms_mean: float
    rms_max: float
    rms_min: float
    rms_std: float
    sample_count: int
    sample_rate_estimate_hz: float

    def to_dict(self) -> dict[str, float | int]:
        """Return a JSON-compatible representation."""
        return asdict(self)


def process_audio_frames(frames: Sequence[Mapping[str, Any]]) -> AudioFeatures:
    """Extract deterministic features from timestamped RMS audio frames."""
    timestamps = [float(frame["ts"]) for frame in frames]
    rms_values = [float(frame["spl"]) for frame in frames]

    return AudioFeatures(
        duration_seconds=duration_seconds(timestamps),
        rms_mean=mean(rms_values),
        rms_max=maximum(rms_values),
        rms_min=minimum(rms_values),
        rms_std=population_std(rms_values),
        sample_count=len(frames),
        sample_rate_estimate_hz=sample_rate_estimate_hz(timestamps),
    )
