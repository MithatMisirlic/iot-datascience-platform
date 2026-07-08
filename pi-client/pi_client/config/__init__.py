"""Environment-based Raspberry Pi client configuration."""

from dataclasses import dataclass
import os
from pathlib import Path


def _boolean(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value.")


@dataclass(frozen=True, slots=True)
class PiClientConfig:
    """Runtime configuration for sensor capture and WebSocket transport."""

    websocket_host: str = "192.168.0.182"
    websocket_port: int = 8080
    websocket_path: str = "/stream"
    imu_enabled: bool = True
    audio_enabled: bool = True
    camera_enabled: bool = False
    mock_mode: bool = False
    imu_rate_hz: float = 60.0
    audio_rate_hz: float = 60.0
    camera_fps: float = 5.0
    reconnect_initial_seconds: float = 1.0
    reconnect_max_seconds: float = 30.0
    i2c_bus: int = 1
    mpu6050_address: int = 0x68
    audio_sample_rate: int = 48_000
    camera_index: int = 0
    camera_jpeg_quality: int = 80
    wav_directory: Path = Path("./recordings")

    @property
    def websocket_url(self) -> str:
        """Return the configured WebSocket URI."""

        path = self.websocket_path
        if not path.startswith("/"):
            path = f"/{path}"
        return f"ws://{self.websocket_host}:{self.websocket_port}{path}"

    @classmethod
    def from_env(cls) -> "PiClientConfig":
        """Load configuration from environment variables."""

        defaults = cls()
        config = cls(
            websocket_host=os.getenv("PI_WS_HOST", defaults.websocket_host),
            websocket_port=int(os.getenv("PI_WS_PORT", str(defaults.websocket_port))),
            websocket_path=os.getenv("PI_WS_PATH", defaults.websocket_path),
            imu_enabled=_boolean("PI_IMU_ENABLED", defaults.imu_enabled),
            audio_enabled=_boolean("PI_AUDIO_ENABLED", defaults.audio_enabled),
            camera_enabled=_boolean("PI_CAMERA_ENABLED", defaults.camera_enabled),
            mock_mode=_boolean("PI_MOCK_MODE", defaults.mock_mode),
            imu_rate_hz=float(
                os.getenv("PI_IMU_RATE_HZ", str(defaults.imu_rate_hz))
            ),
            audio_rate_hz=float(
                os.getenv("PI_AUDIO_RATE_HZ", str(defaults.audio_rate_hz))
            ),
            camera_fps=float(os.getenv("PI_CAMERA_FPS", str(defaults.camera_fps))),
            reconnect_initial_seconds=float(
                os.getenv(
                    "PI_RECONNECT_INITIAL_SECONDS",
                    str(defaults.reconnect_initial_seconds),
                )
            ),
            reconnect_max_seconds=float(
                os.getenv(
                    "PI_RECONNECT_MAX_SECONDS",
                    str(defaults.reconnect_max_seconds),
                )
            ),
            i2c_bus=int(os.getenv("PI_I2C_BUS", str(defaults.i2c_bus))),
            mpu6050_address=int(
                os.getenv("PI_MPU6050_ADDRESS", hex(defaults.mpu6050_address)),
                0,
            ),
            audio_sample_rate=int(
                os.getenv("PI_AUDIO_SAMPLE_RATE", str(defaults.audio_sample_rate))
            ),
            camera_index=int(
                os.getenv("PI_CAMERA_INDEX", str(defaults.camera_index))
            ),
            camera_jpeg_quality=int(
                os.getenv(
                    "PI_CAMERA_JPEG_QUALITY",
                    str(defaults.camera_jpeg_quality),
                )
            ),
            wav_directory=Path(os.getenv("PI_WAV_DIR", str(defaults.wav_directory))),
        )
        config.validate()
        return config

    def validate(self) -> None:
        """Reject unusable transport and capture settings."""

        if not self.websocket_host.strip():
            raise ValueError("PI_WS_HOST must not be empty.")
        if not 1 <= self.websocket_port <= 65_535:
            raise ValueError("PI_WS_PORT must be between 1 and 65535.")
        for name, value in (
            ("PI_IMU_RATE_HZ", self.imu_rate_hz),
            ("PI_AUDIO_RATE_HZ", self.audio_rate_hz),
            ("PI_CAMERA_FPS", self.camera_fps),
            ("PI_RECONNECT_INITIAL_SECONDS", self.reconnect_initial_seconds),
            ("PI_RECONNECT_MAX_SECONDS", self.reconnect_max_seconds),
        ):
            if value <= 0:
                raise ValueError(f"{name} must be greater than zero.")
        if self.reconnect_initial_seconds > self.reconnect_max_seconds:
            raise ValueError(
                "PI_RECONNECT_INITIAL_SECONDS must not exceed the maximum."
            )
        if not 1 <= self.camera_jpeg_quality <= 100:
            raise ValueError("PI_CAMERA_JPEG_QUALITY must be between 1 and 100.")
        if self.audio_sample_rate <= 0:
            raise ValueError("PI_AUDIO_SAMPLE_RATE must be greater than zero.")
        if not 0 <= self.mpu6050_address <= 0x7F:
            raise ValueError("PI_MPU6050_ADDRESS must be a valid 7-bit address.")
        if self.camera_index < 0:
            raise ValueError("PI_CAMERA_INDEX must not be negative.")
