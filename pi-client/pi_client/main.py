"""Raspberry Pi WebSocket streaming client entry point."""

import asyncio
import logging

from pi_client.config import PiClientConfig
from pi_client.recorders.audio import AudioRecorder, MockAudioRecorder
from pi_client.recorders.camera import CameraRecorder, MockCameraRecorder
from pi_client.recorders.motion import MockMotionRecorder, MotionRecorder
from pi_client.websocket_client import SensorWebSocketClient


def build_client(config: PiClientConfig) -> SensorWebSocketClient:
    """Build enabled hardware or mock frame sources from configuration."""

    imu_source = None
    if config.imu_enabled:
        imu_source = (
            MockMotionRecorder()
            if config.mock_mode
            else MotionRecorder(config.i2c_bus, config.mpu6050_address)
        )

    audio_source = None
    if config.audio_enabled:
        audio_class = MockAudioRecorder if config.mock_mode else AudioRecorder
        audio_source = audio_class(
            sample_rate=config.audio_sample_rate,
            frame_rate_hz=config.audio_rate_hz,
            wav_directory=config.wav_directory,
        )

    camera_source = None
    if config.camera_enabled:
        camera_source = (
            MockCameraRecorder()
            if config.mock_mode
            else CameraRecorder(config.camera_index, config.camera_jpeg_quality)
        )

    return SensorWebSocketClient(
        config=config,
        imu_source=imu_source,
        audio_source=audio_source,
        camera_source=camera_source,
    )


async def run() -> None:
    """Load configuration and run until interrupted."""

    config = PiClientConfig.from_env()
    client = build_client(config)
    try:
        await client.run()
    finally:
        await client.close()


def main() -> None:
    """Configure logging and start the asyncio client."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Pi client stopped")


if __name__ == "__main__":
    main()
