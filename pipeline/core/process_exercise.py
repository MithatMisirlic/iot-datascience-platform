"""Exercise-level orchestration for pure sensor feature extraction."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pipeline.core.processing_result import ProcessingResult
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
    """Combine generic summaries and derived series into one dictionary."""
    # This scaled acceleration magnitude is only a placeholder signal for the
    # API's footSpeed field. It is not a physical velocity estimate.
    foot_speed_proxy = tuple(
        acceleration_magnitude * 100.0
        for acceleration_magnitude in acceleration_magnitudes(imu_frames)
    )
    result = ProcessingResult(
        imu=process_imu_frames(imu_frames),
        audio=process_audio_frames(audio_frames),
        mouth=process_mouth_frames(mouth_frames),
        mouth_opening=tuple(
            (float(frame["vertical"]), float(frame["horizontal"]))
            for frame in mouth_frames
        ),
        sound_pressure=tuple(float(frame["spl"]) for frame in audio_frames),
        foot_speed_proxy=foot_speed_proxy,
    )
    return result.to_dict()

