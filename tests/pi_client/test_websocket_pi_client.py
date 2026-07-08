"""Hardware-free tests for Raspberry Pi WebSocket streaming components."""

import asyncio
import base64
import json
from pathlib import Path
import wave

import pytest

from pi_client.config import PiClientConfig
from pi_client.main import build_client
from pi_client.recorders.audio import MockAudioRecorder
from pi_client.recorders import FrameCaptureError
from pi_client.recorders.camera import CameraRecorder, MockCameraRecorder
from pi_client.recorders.motion import MockMotionRecorder, MotionRecorder
from pi_client.websocket_client import SensorWebSocketClient


class FakeI2CBus:
    """Return one fixed MPU6050 register block."""

    def __init__(self) -> None:
        self.writes: list[tuple[int, int, int]] = []

    def write_byte_data(self, address: int, register: int, value: int) -> None:
        self.writes.append((address, register, value))

    def read_i2c_block_data(
        self,
        address: int,
        register: int,
        length: int,
    ) -> list[int]:
        del address, register, length
        return [
            0x7F,
            0xFF,
            0x80,
            0x00,
            0x00,
            0x01,
            0x00,
            0x00,
            0xFF,
            0xFF,
            0x00,
            0x02,
            0x80,
            0x01,
        ]

    def close(self) -> None:
        pass


class FakeWebSocket:
    """Collect serialized WebSocket messages."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    async def send(self, message: str) -> None:
        self.messages.append(message)


class FakeCommandAudio:
    """Capture WAV command dispatch without writing audio."""

    def __init__(self) -> None:
        self.started = 0
        self.stopped = 0

    def read_frame(self) -> dict[str, object]:
        return {"type": "audio", "ts": 1.0, "spl": 0.0}

    def start_wav(self) -> str:
        self.started += 1
        return "started.wav"

    def stop_wav(self) -> str:
        self.stopped += 1
        return "stopped.wav"

    def close(self) -> None:
        pass


class RecoveringFrameSource:
    """Fail once, then return a frame to verify transient recovery."""

    def __init__(self) -> None:
        self.calls = 0

    def read_frame(self) -> dict[str, object]:
        self.calls += 1
        if self.calls == 1:
            raise FrameCaptureError("temporary camera failure")
        return {"type": "camera", "ts": 1.0, "jpeg": "jpeg"}

    def close(self) -> None:
        pass


def test_configuration_defaults_and_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Build the required URI and parse feature toggles from environment."""

    monkeypatch.setenv("PI_WS_HOST", "192.168.0.182")
    monkeypatch.setenv("PI_WS_PORT", "8080")
    monkeypatch.setenv("PI_WS_PATH", "stream")
    monkeypatch.setenv("PI_MOCK_MODE", "true")
    monkeypatch.setenv("PI_CAMERA_ENABLED", "yes")

    config = PiClientConfig.from_env()
    assert config.websocket_url == "ws://192.168.0.182:8080/stream"
    assert config.mock_mode is True
    assert config.camera_enabled is True

    monkeypatch.setenv("PI_AUDIO_ENABLED", "invalid")
    with pytest.raises(ValueError, match="PI_AUDIO_ENABLED"):
        PiClientConfig.from_env()


def test_motion_adapter_and_mock_frames_match_protocol() -> None:
    """Decode signed raw values and preserve exact IMU frame fields."""

    bus = FakeI2CBus()
    recorder = MotionRecorder(bus=bus)
    frame = recorder.read_frame()
    assert bus.writes == [(0x68, 0x6B, 0)]
    assert frame == {
        "type": "imu",
        "ts": frame["ts"],
        "accel_x": 32_767,
        "accel_y": -32_768,
        "accel_z": 1,
        "gyro_x": -1,
        "gyro_y": 2,
        "gyro_z": -32_767,
    }
    assert isinstance(frame["ts"], float)

    mock_frame = MockMotionRecorder().read_frame()
    assert set(mock_frame) == set(frame)


def test_mock_audio_frames_and_wav_commands(tmp_path: Path) -> None:
    """Produce RMS frames and a valid WAV file without audio hardware."""

    recorder = MockAudioRecorder(
        sample_rate=8_000,
        frame_rate_hz=20,
        wav_directory=tmp_path,
    )
    wav_path = recorder.start_wav()
    frame = recorder.read_frame()
    recorder.read_frame()
    assert recorder.stop_wav() == wav_path
    assert frame["type"] == "audio"
    assert isinstance(frame["ts"], float)
    assert isinstance(frame["spl"], float)
    assert frame["spl"] > 0
    with wave.open(str(wav_path), "rb") as wav_file:
        assert wav_file.getframerate() == 8_000
        assert wav_file.getnframes() > 0


def test_mock_camera_frame_contains_base64_jpeg() -> None:
    """Produce a camera frame without OpenCV or a camera device."""

    frame = MockCameraRecorder().read_frame()
    jpeg = base64.b64decode(frame["jpeg"])
    assert frame["type"] == "camera"
    assert isinstance(frame["ts"], float)
    assert jpeg.startswith(b"\xff\xd8")
    assert jpeg.endswith(b"\xff\xd9")


def test_picamera2_recorder_configures_and_encodes_frame(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configure 320x240 capture and preserve the camera frame protocol."""
    import pi_client.recorders.camera as camera_module

    class FakeImage:
        size = 320 * 240 * 3

    class FakeJpeg:
        def tobytes(self) -> bytes:
            return b"\xff\xd8jpeg\xff\xd9"

    class FakeCv2:
        COLOR_RGB2BGR = 1
        IMWRITE_JPEG_QUALITY = 2

        def __init__(self) -> None:
            self.encode_parameters: list[int] | None = None

        @staticmethod
        def cvtColor(image: object, conversion: int) -> object:
            assert isinstance(image, FakeImage)
            assert conversion == FakeCv2.COLOR_RGB2BGR
            return image

        def imencode(
            self,
            extension: str,
            image: object,
            parameters: list[int],
        ) -> tuple[bool, FakeJpeg]:
            assert extension == ".jpg"
            assert isinstance(image, FakeImage)
            self.encode_parameters = parameters
            return True, FakeJpeg()

    class FakePicamera2:
        instance: "FakePicamera2"

        def __init__(self, camera_index: int) -> None:
            assert camera_index == 0
            self.configuration: dict[str, object] | None = None
            self.started = False
            self.stopped = False
            self.closed = False
            FakePicamera2.instance = self

        def create_video_configuration(self, **configuration: object) -> dict[str, object]:
            return configuration

        def configure(self, configuration: dict[str, object]) -> None:
            self.configuration = configuration

        def start(self) -> None:
            self.started = True

        def capture_array(self, stream: str) -> FakeImage:
            assert stream == "main"
            return FakeImage()

        def stop(self) -> None:
            self.stopped = True

        def close(self) -> None:
            self.closed = True

    fake_cv2 = FakeCv2()
    monkeypatch.setattr(camera_module, "Picamera2", FakePicamera2)
    monkeypatch.setattr(camera_module, "cv2", fake_cv2)

    recorder = CameraRecorder(camera_index=0, jpeg_quality=72)
    frame = recorder.read_frame()
    recorder.close()

    assert FakePicamera2.instance.configuration == {
        "main": {"size": (320, 240), "format": "BGR888"},
        "buffer_count": 2,
    }
    assert FakePicamera2.instance.started is True
    assert FakePicamera2.instance.stopped is True
    assert FakePicamera2.instance.closed is True
    assert fake_cv2.encode_parameters == [FakeCv2.IMWRITE_JPEG_QUALITY, 72]
    assert frame["type"] == "camera"
    assert base64.b64decode(frame["jpeg"]) == b"\xff\xd8jpeg\xff\xd9"


def test_frame_producer_skips_recoverable_capture_failure() -> None:
    """Keep the producer alive after one bad camera frame."""

    async def scenario() -> None:
        source = RecoveringFrameSource()
        client = SensorWebSocketClient(PiClientConfig(), camera_source=source)
        queue: asyncio.Queue[dict[str, object]] = asyncio.Queue()
        producer = asyncio.create_task(client._produce_frames(source, 100, queue))
        frame = await asyncio.wait_for(queue.get(), timeout=1)
        client.request_stop()
        await asyncio.wait_for(producer, timeout=1)
        assert source.calls >= 2
        assert frame["type"] == "camera"

    asyncio.run(scenario())


def test_build_client_uses_only_mock_sources() -> None:
    """Construct enabled sources without touching hardware in mock mode."""

    client = build_client(
        PiClientConfig(mock_mode=True, camera_enabled=True)
    )
    assert isinstance(client.imu_source, MockMotionRecorder)
    assert isinstance(client.audio_source, MockAudioRecorder)
    assert isinstance(client.camera_source, MockCameraRecorder)
    asyncio.run(client.close())


def test_server_commands_and_serialized_frame_output() -> None:
    """Dispatch WAV commands and serialize compact protocol JSON."""

    async def scenario() -> None:
        audio = FakeCommandAudio()
        client = SensorWebSocketClient(PiClientConfig(), audio_source=audio)
        await client.handle_server_message('{"cmd":"start_wav"}')
        await client.handle_server_message(b'{"cmd":"stop_wav"}')
        await client.handle_server_message("not-json")
        assert audio.started == 1
        assert audio.stopped == 1

        websocket = FakeWebSocket()
        queue: asyncio.Queue[dict[str, object]] = asyncio.Queue()
        sender = asyncio.create_task(client._send_frames(websocket, queue))
        await queue.put({"type": "audio", "ts": 1.5, "spl": 0.25})
        await asyncio.wait_for(queue.join(), timeout=1)
        sender.cancel()
        await asyncio.gather(sender, return_exceptions=True)
        assert json.loads(websocket.messages[0]) == {
            "type": "audio",
            "ts": 1.5,
            "spl": 0.25,
        }

    asyncio.run(scenario())


def test_reconnect_loop_retries_without_hardware(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retry failed connections until graceful stop is requested."""

    attempts = 0

    class FailingConnection:
        async def __aenter__(self) -> object:
            raise OSError("server unavailable")

        async def __aexit__(self, *args: object) -> None:
            return None

    def failing_connect(*args: object, **kwargs: object) -> FailingConnection:
        nonlocal attempts
        del args, kwargs
        attempts += 1
        return FailingConnection()

    monkeypatch.setattr("pi_client.websocket_client.connect", failing_connect)

    async def scenario() -> None:
        client = SensorWebSocketClient(
            PiClientConfig(
                mock_mode=True,
                imu_enabled=False,
                audio_enabled=False,
                reconnect_initial_seconds=0.01,
                reconnect_max_seconds=0.02,
            )
        )
        task = asyncio.create_task(client.run())
        await asyncio.sleep(0.05)
        client.request_stop()
        await asyncio.wait_for(task, timeout=1)

    asyncio.run(scenario())
    assert attempts >= 2
