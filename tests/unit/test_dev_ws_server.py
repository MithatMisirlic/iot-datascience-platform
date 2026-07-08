"""Tests for the development-only Pi WebSocket receiver."""

import asyncio
import json
from types import SimpleNamespace
from typing import AsyncIterator

from tools.dev_ws_server import DevelopmentWebSocketServer, FrameCounter


class FakeConnection:
    """Minimal asynchronous connection used by the server handler."""

    def __init__(self, path: str, messages: list[str] | None = None) -> None:
        self.request = SimpleNamespace(path=path)
        self.remote_address = ("127.0.0.1", 12345)
        self._messages = iter(messages or [])
        self.close_call: tuple[int, str] | None = None

    def __aiter__(self) -> AsyncIterator[str]:
        return self

    async def __anext__(self) -> str:
        try:
            return next(self._messages)
        except StopIteration as error:
            raise StopAsyncIteration from error

    async def close(self, code: int, reason: str) -> None:
        self.close_call = (code, reason)


def test_frame_counter_counts_known_json_frames_and_resets() -> None:
    counter = FrameCounter()

    assert counter.record(json.dumps({"type": "imu", "ts": 1.0})) is True
    assert counter.record(json.dumps({"type": "audio", "ts": 1.0})) is True
    assert counter.record(json.dumps({"type": "camera", "jpeg": "abc"})) is True
    assert counter.record(json.dumps({"type": "camera", "jpeg": "def"})) is True

    assert counter.snapshot_and_reset() == {"imu": 1, "audio": 1, "camera": 2}
    assert counter.snapshot_and_reset() == {"imu": 0, "audio": 0, "camera": 0}


def test_frame_counter_ignores_malformed_and_unknown_messages() -> None:
    counter = FrameCounter()

    assert counter.record("not-json") is False
    assert counter.record(json.dumps({"type": "status"})) is False
    assert counter.record(json.dumps(["imu"])) is False
    assert counter.snapshot_and_reset() == {"imu": 0, "audio": 0, "camera": 0}


def test_stream_handler_receives_frames_without_sending_commands() -> None:
    async def exercise_handler() -> tuple[dict[str, int], FakeConnection]:
        connection = FakeConnection(
            "/stream",
            [json.dumps({"type": "imu"}), json.dumps({"type": "audio"})],
        )
        server = DevelopmentWebSocketServer()
        await server.handle_connection(connection)  # type: ignore[arg-type]
        return server.counter.snapshot_and_reset(), connection

    counts, connection = asyncio.run(exercise_handler())

    assert counts == {"imu": 1, "audio": 1, "camera": 0}
    assert connection.close_call is None


def test_handler_rejects_paths_other_than_stream() -> None:
    async def exercise_handler() -> FakeConnection:
        connection = FakeConnection("/other")
        server = DevelopmentWebSocketServer()
        await server.handle_connection(connection)  # type: ignore[arg-type]
        return connection

    connection = asyncio.run(exercise_handler())

    assert connection.close_call == (1008, "Use /stream")

