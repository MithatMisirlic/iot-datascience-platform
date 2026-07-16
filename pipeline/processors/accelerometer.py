"""MPU6050 accelerometer and gyroscope feature extraction."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from scipy.signal import find_peaks

from pipeline.core.statistics import (
    coefficient_of_variation,
    duration_seconds,
    magnitude,
    maximum,
    mean,
    minimum,
    population_std,
    population_variance,
    sample_rate_estimate_hz,
)


ACCEL_SCALE = 16_384.0
GYRO_SCALE = 131.0


@dataclass(frozen=True, slots=True)
class ImuFeatures:
    """Generic movement features derived from MPU6050 raw samples.

    Gait speed is an acceleration-derived research proxy. It is not an
    integrated physical walking speed and should not be interpreted clinically.
    """

    duration_seconds: float
    accel_magnitude_mean: float
    accel_magnitude_max: float
    accel_magnitude_min: float
    gyro_magnitude_mean: float
    gyro_magnitude_max: float
    sample_count: int
    sample_rate_estimate_hz: float
    step_count: int
    cadence_steps_per_minute: float
    movement_coefficient_of_variation: float
    movement_variance: float
    movement_standard_deviation: float
    gait_speed_proxy: float
    dominant_frequency_hz: float

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
    sample_rate = sample_rate_estimate_hz(timestamps)
    step_indices = detect_steps(accel_magnitudes, sample_rate)

    return ImuFeatures(
        duration_seconds=duration_seconds(timestamps),
        accel_magnitude_mean=mean(accel_magnitudes),
        accel_magnitude_max=maximum(accel_magnitudes),
        accel_magnitude_min=minimum(accel_magnitudes),
        gyro_magnitude_mean=mean(gyro_magnitudes),
        gyro_magnitude_max=maximum(gyro_magnitudes),
        sample_count=len(frames),
        sample_rate_estimate_hz=sample_rate,
        step_count=len(step_indices),
        cadence_steps_per_minute=cadence_steps_per_minute(len(step_indices), timestamps),
        movement_coefficient_of_variation=coefficient_of_variation(accel_magnitudes),
        movement_variance=population_variance(accel_magnitudes),
        movement_standard_deviation=population_std(accel_magnitudes),
        gait_speed_proxy=gait_speed_proxy(accel_magnitudes),
        dominant_frequency_hz=dominant_frequency_hz(accel_magnitudes, sample_rate),
    )


def detect_steps(accel_magnitudes: Sequence[float], sample_rate_hz: float) -> list[int]:
    """Detect step-like peaks in acceleration magnitude."""
    if len(accel_magnitudes) < 3:
        return []
    samples = np.asarray(accel_magnitudes, dtype=float)
    dynamic = samples - float(np.median(samples))
    spread = float(np.std(dynamic))
    if spread == 0.0:
        return []
    distance = max(1, int(round(max(sample_rate_hz, 1.0) * 0.25)))
    prominence = max(0.05, spread * 0.5)
    peaks, _ = find_peaks(dynamic, prominence=prominence, distance=distance)
    return [int(index) for index in peaks]


def cadence_steps_per_minute(step_count: int, timestamps: Sequence[float]) -> float:
    """Return cadence from detected steps and recording duration."""
    duration = duration_seconds(timestamps)
    if duration == 0.0:
        return 0.0
    return float(step_count / duration * 60.0)


def gait_speed_proxy(accel_magnitudes: Sequence[float]) -> float:
    """Return mean dynamic acceleration scaled as a gait-speed proxy.

    This is an acceleration-derived estimate for exploratory comparison only.
    It is not physically integrated speed and is not medically validated.
    """
    if not accel_magnitudes:
        return 0.0
    baseline = float(np.median(np.asarray(accel_magnitudes, dtype=float)))
    dynamic = [abs(float(value) - baseline) for value in accel_magnitudes]
    return mean(dynamic) * 100.0


def dominant_frequency_hz(values: Sequence[float], sample_rate_hz: float) -> float:
    """Estimate dominant non-DC frequency using FFT magnitude."""
    if len(values) < 3 or sample_rate_hz <= 0.0:
        return 0.0
    samples = np.asarray(values, dtype=float)
    samples = samples - float(np.mean(samples))
    if np.allclose(samples, 0.0):
        return 0.0
    frequencies = np.fft.rfftfreq(samples.size, d=1.0 / sample_rate_hz)
    magnitudes = np.abs(np.fft.rfft(samples))
    if magnitudes.size <= 1:
        return 0.0
    magnitudes[0] = 0.0
    index = int(np.argmax(magnitudes))
    return float(frequencies[index])
