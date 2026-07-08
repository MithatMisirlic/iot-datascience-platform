"""Generic processing result and OpenAPI compatibility transformation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import statistics
from typing import Any

from pipeline.processors.accelerometer import ImuFeatures
from pipeline.processors.audio import AudioFeatures
from pipeline.processors.image import MouthFeatures


@dataclass(frozen=True, slots=True)
class ProcessingResult:
    """Combined generic sensor summaries and their derived sample series."""

    imu: ImuFeatures
    audio: AudioFeatures
    mouth: MouthFeatures
    mouth_opening: tuple[tuple[float, float], ...]
    sound_pressure: tuple[float, ...]
    foot_speed_proxy: tuple[float, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible generic feature dictionary."""
        return {
            "imu": self.imu.to_dict(),
            "audio": self.audio.to_dict(),
            "mouth": self.mouth.to_dict(),
            "signals": {
                "mouth_opening": [list(sample) for sample in self.mouth_opening],
                "sound_pressure": list(self.sound_pressure),
                "foot_speed_proxy": list(self.foot_speed_proxy),
            },
        }


def _median(values: Sequence[float]) -> float | None:
    return statistics.median(values) if values else None


def _present(values: Mapping[str, float | None]) -> dict[str, float]:
    return {name: value for name, value in values.items() if value is not None}


def to_exercise_data(processed: Mapping[str, Any]) -> dict[str, Any]:
    """Transform generic features into the OpenAPI processor-output shape.

    The foot-speed values are acceleration-magnitude proxies scaled for an
    early research workflow. They are not physical speed measurements,
    medical predictions, diagnostic outputs, or validated clinical features.
    """
    imu = processed["imu"]
    audio = processed["audio"]
    mouth = processed["mouth"]
    signals = processed["signals"]

    mouth_values = [
        [float(sample[0]), float(sample[1])]
        for sample in signals["mouth_opening"]
    ]
    sound_values = [float(value) for value in signals["sound_pressure"]]
    foot_speed_values = [float(value) for value in signals["foot_speed_proxy"]]
    vertical_values = [sample[0] for sample in mouth_values]
    horizontal_values = [sample[1] for sample in mouth_values]

    averages = _present(
        {
            "mouthOpeningVertical": (
                float(mouth["mouth_vertical_mean"]) if vertical_values else None
            ),
            "mouthOpeningHorizontal": (
                float(mouth["mouth_horizontal_mean"]) if horizontal_values else None
            ),
            "soundPressure": (
                float(audio["rms_mean"]) if sound_values else None
            ),
            "footSpeed": (
                statistics.fmean(foot_speed_values) if foot_speed_values else None
            ),
        }
    )
    medians = _present(
        {
            "mouthOpeningVertical": _median(vertical_values),
            "mouthOpeningHorizontal": _median(horizontal_values),
            "soundPressure": _median(sound_values),
            "footSpeed": _median(foot_speed_values),
        }
    )

    return {
        "mouthOpening": {
            "values": mouth_values,
            "sampleRate": float(mouth["sample_rate_estimate_hz"]),
        },
        "soundPressure": {
            "values": sound_values,
            "sampleRate": float(audio["sample_rate_estimate_hz"]),
        },
        "footSpeed": {
            "values": foot_speed_values,
            "sampleRate": float(imu["sample_rate_estimate_hz"]),
            "unit": "cm/s",
        },
        "aggregates": {
            "stepLengths": {"values": [], "unit": "cm"},
            "averages": averages,
            "medians": medians,
        },
    }

