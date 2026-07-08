"""Unit tests for deterministic sensor feature extraction."""

import pytest

from pipeline.core.process_exercise import process_exercise
from pipeline.core.processing_result import to_exercise_data
from pipeline.processors.accelerometer import process_imu_frames
from pipeline.processors.audio import process_audio_frames
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

    assert set(result) == {"imu", "audio", "mouth", "signals"}
    assert result["imu"]["sample_count"] == 2
    assert result["audio"]["sample_count"] == 2
    assert result["mouth"]["sample_count"] == 2
    assert result["signals"] == {
        "mouth_opening": [[2.0, 1.0], [4.0, 2.0]],
        "sound_pressure": [1.0, 3.0],
        "foot_speed_proxy": [100.0, 200.0],
    }


def test_openapi_exercise_data_compatible_output_shape() -> None:
    generic = process_exercise(IMU_FRAMES, AUDIO_FRAMES, MOUTH_FRAMES)
    output = to_exercise_data(generic)

    assert set(output) == {
        "mouthOpening",
        "soundPressure",
        "footSpeed",
        "aggregates",
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


def test_empty_aggregation_remains_openapi_compatible() -> None:
    output = to_exercise_data(process_exercise([], [], []))

    assert output["mouthOpening"] == {"values": [], "sampleRate": 0.0}
    assert output["soundPressure"] == {"values": [], "sampleRate": 0.0}
    assert output["footSpeed"]["values"] == []
    assert output["aggregates"]["averages"] == {}
    assert output["aggregates"]["medians"] == {}
