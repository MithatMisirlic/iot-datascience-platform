"""MPU6050 and mock IMU frame sources."""

from typing import Any, Protocol
import time

from pi_client.recorders import HardwareUnavailableError

try:
    from smbus2 import SMBus
except ImportError:  # pragma: no cover - depends on Pi system packages
    SMBus = None  # type: ignore[assignment,misc]


class I2CBus(Protocol):
    """Minimal I2C operations used by the MPU6050 adapter."""

    def write_byte_data(self, address: int, register: int, value: int) -> None: ...

    def read_i2c_block_data(
        self,
        address: int,
        register: int,
        length: int,
    ) -> list[int]: ...

    def close(self) -> None: ...


class MotionRecorder:
    """Read raw MPU6050 acceleration and gyroscope values."""

    DATA_REGISTER = 0x3B
    POWER_REGISTER = 0x6B

    def __init__(
        self,
        bus_number: int = 1,
        address: int = 0x68,
        bus: I2CBus | None = None,
    ) -> None:
        owns_bus = bus is None
        if bus is None:
            if SMBus is None:
                raise HardwareUnavailableError(
                    "smbus2 is unavailable; use PI_MOCK_MODE=true off the Pi."
                )
            bus = SMBus(bus_number)
        self._bus = bus
        self._address = address
        self._owns_bus = owns_bus
        self._bus.write_byte_data(self._address, self.POWER_REGISTER, 0)

    @staticmethod
    def _signed(high: int, low: int) -> int:
        value = (high << 8) | low
        return value - 65_536 if value >= 32_768 else value

    def read_frame(self) -> dict[str, Any]:
        """Return one protocol-compatible raw IMU frame."""

        data = self._bus.read_i2c_block_data(
            self._address,
            self.DATA_REGISTER,
            14,
        )
        if len(data) != 14:
            raise OSError("MPU6050 returned an incomplete frame.")
        return {
            "type": "imu",
            "ts": time.time(),
            "accel_x": self._signed(data[0], data[1]),
            "accel_y": self._signed(data[2], data[3]),
            "accel_z": self._signed(data[4], data[5]),
            "gyro_x": self._signed(data[8], data[9]),
            "gyro_y": self._signed(data[10], data[11]),
            "gyro_z": self._signed(data[12], data[13]),
        }

    def close(self) -> None:
        """Close the I2C bus owned by this recorder."""

        if self._owns_bus:
            self._bus.close()


class MockMotionRecorder:
    """Generate deterministic raw IMU frames without I2C hardware."""

    def __init__(self) -> None:
        self._sample = 0

    def read_frame(self) -> dict[str, Any]:
        """Return one deterministic mock IMU frame."""

        self._sample += 1
        offset = self._sample % 100
        return {
            "type": "imu",
            "ts": time.time(),
            "accel_x": offset,
            "accel_y": -offset,
            "accel_z": 16_384,
            "gyro_x": offset * 2,
            "gyro_y": -(offset * 2),
            "gyro_z": 0,
        }

    def close(self) -> None:
        """Require no mock cleanup."""
