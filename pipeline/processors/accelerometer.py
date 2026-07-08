"""MPU6050 accelerometer and gyroscope feature extraction."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from pipeline.core.statistics import (
    duration_seconds,
    magnitude,
    maximum,
    mean,
    minimum,
    sample_rate_estimate_hz,
)


ACCEL_SCALE = 16_384.0
GYRO_SCALE = 131.0


@dataclass(frozen=True, slots=True)
class ImuFeatures:
    """Generic summary features derived from MPU6050 raw samples."""

    duration_seconds: float
    accel_magnitude_mean: float
    accel_magnitude_max: float
    accel_magnitude_min: float
    gyro_magnitude_mean: float
    gyro_magnitude_max: float
    sample_count: int
    sample_rate_estimate_hz: float

    def to_dict(self) -> dict[str, float | int]:
        """Return a JSON-compatible representation."""
        return asdict(self)


def acceleration_magnitudes(
    frames: Sequence[Mapping[str, Any]],
) -> list[float]:
    """Convert raw accelerometer axes to g and return vector magnitudes."""
    return [
        magnitude(
            float(frame["accel_x"]) / ACCEL_SCALE,
            float(frame["accel_y"]) / ACCEL_SCALE,
            float(frame["accel_z"]) / ACCEL_SCALE,
        )
        for frame in frames
    ]


def process_imu_frames(frames: Sequence[Mapping[str, Any]]) -> ImuFeatures:
    """Extract deterministic IMU features from raw MPU6050 frames."""
    timestamps = [float(frame["ts"]) for frame in frames]
    accel_magnitudes = acceleration_magnitudes(frames)
    gyro_magnitudes = [
        magnitude(
            float(frame["gyro_x"]) / GYRO_SCALE,
            float(frame["gyro_y"]) / GYRO_SCALE,
            float(frame["gyro_z"]) / GYRO_SCALE,
        )
        for frame in frames
    ]

    return ImuFeatures(
        duration_seconds=duration_seconds(timestamps),
        accel_magnitude_mean=mean(accel_magnitudes),
        accel_magnitude_max=maximum(accel_magnitudes),
        accel_magnitude_min=minimum(accel_magnitudes),
        gyro_magnitude_mean=mean(gyro_magnitudes),
        gyro_magnitude_max=maximum(gyro_magnitudes),
        sample_count=len(frames),
        sample_rate_estimate_hz=sample_rate_estimate_hz(timestamps),
    )
