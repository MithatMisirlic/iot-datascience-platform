"""Cross-application domain enumerations."""

from enum import Enum


class RecordingStatus(str, Enum):
    """Recording states defined by the API contract."""

    IDLE = "idle"
    RECORDING = "recording"
    STOPPED = "stopped"


class SensorFileType(str, Enum):
    """File categories accepted from a recording device."""

    ACCEL = "accel"
    GYRO = "gyro"
    AUDIO = "audio"
    MOUTH = "mouth"
    VIDEO = "video"
