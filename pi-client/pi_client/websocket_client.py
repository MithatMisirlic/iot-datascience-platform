"""Asynchronous WebSocket transport for Raspberry Pi sensor frames."""

import asyncio
import json
import logging
from typing import Any, Protocol

from websockets.asyncio.client import ClientConnection, connect

from pi_client.config import PiClientConfig
from pi_client.recorders import FrameCaptureError


logger = logging.getLogger(__name__)


class FrameSource(Protocol):
    """Blocking sensor source executed in an asyncio worker thread."""

    def read_frame(self) -> dict[str, Any]: ...

    def close(self) -> None: ...


class AudioFrameSource(FrameSource, Protocol):
    """Audio source that can optionally write commanded WAV recordings."""

    def start_wav(self) -> object: ...

    def stop_wav(self) -> object: ...


class SensorWebSocketClient:
    """Stream enabled sensor sources and receive recording commands."""

    def __init__(
        self,
        config: PiClientConfig,
        imu_source: FrameSource | None = None,
        audio_source: AudioFrameSource | None = None,
        camera_source: FrameSource | None = None,
    ) -> None:
        self.config = config
        self.imu_source = imu_source
        self.audio_source = audio_source
        self.camera_source = camera_source
        self._stop_event = asyncio.Event()

    async def run(self) -> None:
        """Connect, stream, and reconnect until stop is requested."""

        reconnect_delay = self.config.reconnect_initial_seconds
        while not self._stop_event.is_set():
            try:
                logger.info("Connecting to %s", self.config.websocket_url)
                async with connect(
                    self.config.websocket_url,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=5,
                    max_queue=32,
                ) as websocket:
                    logger.info("WebSocket connected")
                    reconnect_delay = self.config.reconnect_initial_seconds
                    await self._run_connection(websocket)
            except asyncio.CancelledError:
                raise
            except Exception:
                if self._stop_event.is_set():
                    break
                logger.exception(
                    "WebSocket connection failed; retrying in %.1f seconds",
                    reconnect_delay,
                )
                await self._wait_or_stop(reconnect_delay)
                reconnect_delay = min(
                    reconnect_delay * 2,
                    self.config.reconnect_max_seconds,
                )

    async def _run_connection(self, websocket: ClientConnection) -> None:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=256)
        tasks: list[asyncio.Task[Any]] = [
            asyncio.create_task(self._send_frames(websocket, queue)),
            asyncio.create_task(self._receive_commands(websocket)),
        ]
        if self.imu_source is not None:
            tasks.append(
                asyncio.create_task(
                    self._produce_frames(
                        self.imu_source,
                        self.config.imu_rate_hz,
                        queue,
                    )
                )
            )
        if self.audio_source is not None:
            tasks.append(
                asyncio.create_task(
                    self._produce_frames(
                        self.audio_source,
                        self.config.audio_rate_hz,
                        queue,
                    )
                )
            )
        if self.camera_source is not None:
            tasks.append(
                asyncio.create_task(
                    self._produce_frames(
                        self.camera_source,
                        self.config.camera_fps,
                        queue,
                    )
                )
            )

        stop_task = asyncio.create_task(self._stop_event.wait())
        done, pending = await asyncio.wait(
            [*tasks, stop_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        if stop_task in done:
            for task in done:
                if task is not stop_task and not task.cancelled():
                    task.exception()
            return
        for task in done:
            task.result()
        raise ConnectionError("WebSocket connection closed.")

    async def _produce_frames(
        self,
        source: FrameSource,
        rate_hz: float,
        queue: asyncio.Queue[dict[str, Any]],
    ) -> None:
        interval = 1.0 / rate_hz
        loop = asyncio.get_running_loop()
        next_tick = loop.time()
        while not self._stop_event.is_set():
            try:
                frame = await asyncio.to_thread(source.read_frame)
            except FrameCaptureError as error:
                logger.warning(
                    "Skipping failed frame from %s: %s",
                    type(source).__name__,
                    error,
                )
            else:
                await queue.put(frame)
            next_tick += interval
            now = loop.time()
            if next_tick < now - interval:
                next_tick = now
            await asyncio.sleep(max(0.0, next_tick - now))

    @staticmethod
    async def _send_frames(
        websocket: ClientConnection,
        queue: asyncio.Queue[dict[str, Any]],
    ) -> None:
        while True:
            frame = await queue.get()
            try:
                await websocket.send(json.dumps(frame, separators=(",", ":")))
            finally:
                queue.task_done()

    async def _receive_commands(self, websocket: ClientConnection) -> None:
        async for message in websocket:
            await self.handle_server_message(message)
        raise ConnectionError("WebSocket server closed the connection.")

    async def handle_server_message(self, message: str | bytes) -> None:
        """Parse and dispatch one server command."""

        if isinstance(message, bytes):
            message = message.decode("utf-8")
        try:
            payload = json.loads(message)
        except (UnicodeDecodeError, json.JSONDecodeError):
            logger.warning("Ignoring malformed WebSocket command")
            return
        if not isinstance(payload, dict):
            logger.warning("Ignoring non-object WebSocket command")
            return

        command = payload.get("cmd")
        if command == "start_wav":
            if self.audio_source is None:
                logger.warning("Ignoring start_wav because audio is disabled")
                return
            path = await asyncio.to_thread(self.audio_source.start_wav)
            logger.info("WAV recording started: %s", path)
        elif command == "stop_wav":
            if self.audio_source is None:
                logger.warning("Ignoring stop_wav because audio is disabled")
                return
            path = await asyncio.to_thread(self.audio_source.stop_wav)
            logger.info("WAV recording stopped: %s", path)
        else:
            logger.warning("Ignoring unsupported WebSocket command: %r", command)

    async def _wait_or_stop(self, delay: float) -> None:
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=delay)
        except TimeoutError:
            pass

    def request_stop(self) -> None:
        """Request graceful shutdown of streaming and reconnect loops."""

        self._stop_event.set()

    async def close(self) -> None:
        """Stop and close all configured frame sources."""

        self.request_stop()
        sources = (self.imu_source, self.audio_source, self.camera_source)
        await asyncio.gather(
            *(
                asyncio.to_thread(source.close)
                for source in sources
                if source is not None
            ),
            return_exceptions=True,
        )
