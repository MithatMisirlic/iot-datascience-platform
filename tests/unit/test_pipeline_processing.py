"""Unit tests for deterministic sensor feature extraction."""

import math

import pytest

from pipeline.core.process_exercise import process_exercise
from pipeline.core.processing_result import to_exercise_data
from pipeline.processors.accelerometer import (
    detect_steps,
    dominant_frequency_hz,
    process_imu_frames,
)
from pipeline.processors.audio import (
    mfcc_summary,
    process_audio_frames,
    syllable_timing_summary,
)
from pipeline.processors.image import process_mouth_frames


IMU_FRAMES = [
    {
        "ts": 10.0,
        "accel_x": 16_384,
        "accel_y": 0,
        "accel_z": 0,
        "gyro_x": 131,
        "gyro_y": 0,
        "gyro_z": 0,
    },
    {
        "ts": 11.0,
        "accel_x": 0,
        "accel_y": 32_768,
        "accel_z": 0,
        "gyro_x": 0,
        "gyro_y": 262,
        "gyro_z": 0,
    },
]
AUDIO_FRAMES = [{"ts": 10.0, "spl": 1.0}, {"ts": 10.5, "spl": 3.0}]
MOUTH_FRAMES = [
    {"ts": 10.0, "vertical": 2.0, "horizontal": 1.0},
    {"ts": 12.0, "vertical": 4.0, "horizontal": 2.0},
]


def test_imu_feature_extraction_applies_mpu6050_scales() -> None:
    features = process_imu_frames(IMU_FRAMES)

    assert features.duration_seconds == 1.0
    assert features.accel_magnitude_mean == 1.5
    assert features.accel_magnitude_max == 2.0
    assert features.accel_magnitude_min == 1.0
    assert features.gyro_magnitude_mean == 1.5
    assert features.gyro_magnitude_max == 2.0
    assert features.sample_count == 2
    assert features.sample_rate_estimate_hz == 1.0


def test_audio_feature_extraction() -> None:
    features = process_audio_frames(AUDIO_FRAMES)

    assert features.duration_seconds == 0.5
    assert features.rms_mean == 2.0
    assert features.rms_max == 3.0
    assert features.rms_min == 1.0
    assert features.rms_std == 1.0
    assert features.sample_count == 2
    assert features.sample_rate_estimate_hz == 2.0


def test_mouth_and_mar_feature_extraction() -> None:
    features = process_mouth_frames(MOUTH_FRAMES)

    assert features.duration_seconds == 2.0
    assert features.mouth_vertical_mean == 3.0
    assert features.mouth_vertical_max == 4.0
    assert features.mouth_vertical_min == 2.0
    assert features.mouth_horizontal_mean == 1.5
    assert features.mouth_horizontal_max == 2.0
    assert features.mouth_horizontal_min == 1.0
    assert features.mar_mean == 2.0
    assert features.mar_max == 2.0
    assert features.mar_min == 2.0
    assert features.sample_count == 2
    assert features.sample_rate_estimate_hz == 0.5


@pytest.mark.parametrize(
    ("processor", "sample_count"),
    [
        (process_imu_frames, 0),
        (process_audio_frames, 0),
        (process_mouth_frames, 0),
    ],
)
def test_processors_handle_empty_input(processor: object, sample_count: int) -> None:
    features = processor([])  # type: ignore[operator]

    assert features.sample_count == sample_count
    assert features.duration_seconds == 0.0
    assert features.sample_rate_estimate_hz == 0.0


def test_zero_horizontal_mouth_opening_produces_zero_mar() -> None:
    features = process_mouth_frames(
        [{"ts": 1.0, "vertical": 5.0, "horizontal": 0.0}]
    )

    assert features.mar_mean == 0.0
    assert features.mar_max == 0.0
    assert features.mar_min == 0.0


def test_exercise_aggregation_output_shape() -> None:
    result = process_exercise(IMU_FRAMES, AUDIO_FRAMES, MOUTH_FRAMES)

    assert set(result) == {"imu", "audio", "mouth", "signals", "report"}
    assert result["imu"]["sample_count"] == 2
    assert result["audio"]["sample_count"] == 2
    assert result["mouth"]["sample_count"] == 2
    assert result["signals"] == {
        "mouth_opening": [[2.0, 1.0], [4.0, 2.0]],
        "sound_pressure": [1.0, 3.0],
        "foot_speed_proxy": [100.0, 200.0],
    }
    assert set(result["report"]) == {"audio", "movement", "vision", "overall"}


def test_openapi_exercise_data_compatible_output_shape() -> None:
    generic = process_exercise(IMU_FRAMES, AUDIO_FRAMES, MOUTH_FRAMES)
    output = to_exercise_data(generic)

    assert set(output) == {
        "mouthOpening",
        "soundPressure",
        "footSpeed",
        "aggregates",
        "metadata",
    }
    assert output["mouthOpening"] == {
        "values": [[2.0, 1.0], [4.0, 2.0]],
        "sampleRate": 0.5,
    }
    assert output["soundPressure"] == {
        "values": [1.0, 3.0],
        "sampleRate": 2.0,
    }
    assert output["footSpeed"] == {
        "values": [100.0, 200.0],
        "sampleRate": 1.0,
        "unit": "cm/s",
    }
    assert output["aggregates"] == {
        "stepLengths": {"values": [], "unit": "cm"},
        "averages": {
            "mouthOpeningVertical": 3.0,
            "mouthOpeningHorizontal": 1.5,
            "soundPressure": 2.0,
            "footSpeed": 150.0,
        },
        "medians": {
            "mouthOpeningVertical": 3.0,
            "mouthOpeningHorizontal": 1.5,
            "soundPressure": 2.0,
            "footSpeed": 150.0,
        },
    }
    assert set(output["metadata"]) == {"analysis"}


def test_empty_aggregation_remains_openapi_compatible() -> None:
    output = to_exercise_data(process_exercise([], [], []))

    assert output["mouthOpening"] == {"values": [], "sampleRate": 0.0}
    assert output["soundPressure"] == {"values": [], "sampleRate": 0.0}
    assert output["footSpeed"]["values"] == []
    assert output["aggregates"]["averages"] == {}
    assert output["aggregates"]["medians"] == {}
    assert output["metadata"]["analysis"]["overall"]["completeness"] == {
        "imu": 0.0,
        "audio": 0.0,
        "vision": 0.0,
    }


def test_mfcc_extraction_returns_13_finite_coefficients() -> None:
    means, stds = mfcc_summary([0.1, 0.4, 0.2, 0.5, 0.1, 0.3], 6.0)

    assert len(means) == 13
    assert len(stds) == 13
    assert all(math.isfinite(value) for value in means)
    assert all(value >= 0.0 for value in stds)


def test_syllable_detector_counts_envelope_peaks() -> None:
    count, average_duration, rate = syllable_timing_summary(
        [0.0, 1.0, 0.0, 1.0, 0.0],
        [0.0, 0.25, 0.5, 0.75, 1.0],
    )

    assert count == 2
    assert average_duration == pytest.approx(0.25)
    assert rate == pytest.approx(2.0)


def test_step_detection_counts_acceleration_peaks() -> None:
    assert detect_steps([1.0, 1.8, 1.0, 1.9, 1.0], sample_rate_hz=5.0) == [1, 3]


def test_tremor_fft_estimates_dominant_frequency() -> None:
    sample_rate = 20.0
    values = [
        math.sin(2.0 * math.pi * 2.0 * index / sample_rate)
        for index in range(100)
    ]

    assert dominant_frequency_hz(values, sample_rate) == pytest.approx(2.0)


def test_jaw_tracking_metrics() -> None:
    features = process_mouth_frames(
        [
            {"ts": 0.0, "vertical": 1.0, "horizontal": 2.0, "jaw_x": 0.0, "jaw_y": 0.0},
            {"ts": 1.0, "vertical": 2.0, "horizontal": 2.0, "jaw_x": 0.0, "jaw_y": 1.0},
            {"ts": 2.0, "vertical": 3.0, "horizontal": 2.0, "jaw_x": 0.0, "jaw_y": 3.0},
        ]
    )

    assert features.frame_count == 3
    assert features.processed_frame_count == 3
    assert features.jaw_movement_amplitude == pytest.approx(3.0)
    assert features.average_jaw_speed == pytest.approx(1.5)


def test_no_face_handling_keeps_frame_count_without_processed_geometry() -> None:
    features = process_mouth_frames(
        [{"ts": 0.0, "face_detected": False}]
    )

    assert features.frame_count == 1
    assert features.processed_frame_count == 0
    assert features.mar_mean == 0.0
    assert features.average_jaw_speed == 0.0


def test_cross_modal_report_contains_descriptive_metrics() -> None:
    result = process_exercise(IMU_FRAMES, AUDIO_FRAMES, MOUTH_FRAMES)
    cross_modal = result["report"]["overall"]["cross_modal"]

    assert set(cross_modal) == {
        "speech_activity_while_moving",
        "average_mouth_opening_during_high_movement",
    }
    assert 0.0 <= cross_modal["speech_activity_while_moving"] <= 1.0
