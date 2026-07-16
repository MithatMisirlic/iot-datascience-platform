"""Exercise-level orchestration for pure sensor feature extraction."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from pipeline.core.processing_result import ProcessingResult
from pipeline.core.statistics import duration_seconds, mean, sample_rate_estimate_hz
from pipeline.processors.accelerometer import (
    acceleration_magnitudes,
    process_imu_frames,
)
from pipeline.processors.audio import process_audio_frames
from pipeline.processors.image import process_mouth_frames


def process_exercise(
    imu_frames: Sequence[Mapping[str, Any]],
    audio_frames: Sequence[Mapping[str, Any]],
    mouth_frames: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Combine modality summaries, derived signals, and report metadata."""
    imu_features = process_imu_frames(imu_frames)
    audio_features = process_audio_frames(audio_frames)
    mouth_features = process_mouth_frames(mouth_frames)
    accel_magnitudes = acceleration_magnitudes(imu_frames)

    # This scaled acceleration magnitude is only a placeholder signal for the
    # API's footSpeed field. It is not a physical velocity estimate.
    foot_speed_proxy = tuple(
        acceleration_magnitude * 100.0
        for acceleration_magnitude in accel_magnitudes
    )
    mouth_opening = tuple(
        (float(frame["vertical"]), float(frame["horizontal"]))
        for frame in mouth_frames
        if frame.get("face_detected", True) is not False
        and "vertical" in frame
        and "horizontal" in frame
    )
    sound_pressure = tuple(float(frame["spl"]) for frame in audio_frames)
    report = build_analysis_report(
        imu_features.to_dict(),
        audio_features.to_dict(),
        mouth_features.to_dict(),
        imu_frames,
        audio_frames,
        mouth_frames,
        accel_magnitudes,
        mouth_opening,
        sound_pressure,
    )
    result = ProcessingResult(
        imu=imu_features,
        audio=audio_features,
        mouth=mouth_features,
        mouth_opening=mouth_opening,
        sound_pressure=sound_pressure,
        foot_speed_proxy=foot_speed_proxy,
        report=report,
    )
    return result.to_dict()


def build_analysis_report(
    movement: Mapping[str, Any],
    audio: Mapping[str, Any],
    vision: Mapping[str, Any],
    imu_frames: Sequence[Mapping[str, Any]],
    audio_frames: Sequence[Mapping[str, Any]],
    mouth_frames: Sequence[Mapping[str, Any]],
    accel_magnitudes: Sequence[float],
    mouth_opening: Sequence[tuple[float, float]],
    sound_pressure: Sequence[float],
) -> dict[str, Any]:
    """Build a unified descriptive multi-modal analysis report."""
    timestamps = {
        "imu": [float(frame["ts"]) for frame in imu_frames],
        "audio": [float(frame["ts"]) for frame in audio_frames],
        "vision": [float(frame["ts"]) for frame in mouth_frames if "ts" in frame],
    }
    all_timestamps = [value for values in timestamps.values() for value in values]
    experiment_duration = duration_seconds(all_timestamps)
    sample_rates = {
        name: sample_rate_estimate_hz(values) for name, values in timestamps.items()
    }
    completeness = {
        "imu": 1.0 if imu_frames else 0.0,
        "audio": 1.0 if audio_frames else 0.0,
        "vision": float(vision.get("processed_frame_count", 0)) / max(len(mouth_frames), 1),
    }
    return {
        "audio": dict(audio),
        "movement": dict(movement),
        "vision": dict(vision),
        "overall": {
            "experiment_duration": experiment_duration,
            "synchronization": synchronization_summary(timestamps),
            "sensor_sample_rates": sample_rates,
            "processing_timestamp_utc": datetime.now(UTC).isoformat(),
            "completeness": completeness,
            "processing_duration_seconds": 0.0,
            "cross_modal": cross_modal_metrics(
                accel_magnitudes,
                sound_pressure,
                mouth_opening,
            ),
        },
    }


def synchronization_summary(timestamps: Mapping[str, Sequence[float]]) -> dict[str, float | None]:
    """Return simple timestamp alignment information across modalities."""
    starts = [min(values) for values in timestamps.values() if values]
    ends = [max(values) for values in timestamps.values() if values]
    if not starts or not ends:
        return {
            "start_offset_seconds": None,
            "end_offset_seconds": None,
        }
    return {
        "start_offset_seconds": max(starts) - min(starts),
        "end_offset_seconds": max(ends) - min(ends),
    }


def cross_modal_metrics(
    accel_magnitudes: Sequence[float],
    sound_pressure: Sequence[float],
    mouth_opening: Sequence[tuple[float, float]],
) -> dict[str, float]:
    """Compute descriptive cross-modal statistics only."""
    paired_count = min(len(accel_magnitudes), len(sound_pressure))
    if paired_count == 0:
        speech_activity_while_moving = 0.0
    else:
        movement_threshold = mean(accel_magnitudes) if accel_magnitudes else 0.0
        speech_threshold = mean(sound_pressure) if sound_pressure else 0.0
        active_pairs = sum(
            1
            for index in range(paired_count)
            if accel_magnitudes[index] >= movement_threshold
            and sound_pressure[index] >= speech_threshold
        )
        speech_activity_while_moving = active_pairs / paired_count

    mouth_count = min(len(accel_magnitudes), len(mouth_opening))
    high_movement_openings: list[float] = []
    if mouth_count:
        movement_threshold = mean(accel_magnitudes)
        high_movement_openings = [
            float(mouth_opening[index][0])
            for index in range(mouth_count)
            if accel_magnitudes[index] >= movement_threshold
        ]
    return {
        "speech_activity_while_moving": float(speech_activity_while_moving),
        "average_mouth_opening_during_high_movement": mean(high_movement_openings),
    }
