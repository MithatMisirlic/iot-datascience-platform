"""Development-only WebSocket receiver for Raspberry Pi sensor frames."""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
import json
import logging
from typing import Final

from websockets.asyncio.server import ServerConnection, serve


HOST: Final = "0.0.0.0"
PORT: Final = 8080
STREAM_PATH: Final = "/stream"
FRAME_TYPES: Final = ("imu", "audio", "camera")

logger = logging.getLogger(__name__)


class FrameCounter:
    """Count recognized Pi frames between reporting intervals."""

    def __init__(self) -> None:
        self._counts: Counter[str] = Counter()

    def record(self, message: str | bytes) -> bool:
        """Record a valid frame type and return whether it was recognized."""
        try:
            payload = json.loads(message)
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
            logger.warning("Ignoring malformed JSON WebSocket message")
            return False

        if not isinstance(payload, dict) or payload.get("type") not in FRAME_TYPES:
            logger.warning("Ignoring JSON message with unknown frame type")
            return False

        self._counts[payload["type"]] += 1
        return True

    def snapshot_and_reset(self) -> dict[str, int]:
        """Return the current interval totals and begin a new interval."""
        snapshot = {frame_type: self._counts[frame_type] for frame_type in FRAME_TYPES}
        self._counts.clear()
        return snapshot


class DevelopmentWebSocketServer:
    """Receive Pi frames without invoking backend or processing behavior."""

    def __init__(self, counter: FrameCounter | None = None) -> None:
        self.counter = counter or FrameCounter()

    async def handle_connection(self, websocket: ServerConnection) -> None:
        """Consume frames from one `/stream` connection."""
        request = getattr(websocket, "request", None)
        path = getattr(request, "path", None)
        if path != STREAM_PATH:
            await websocket.close(code=1008, reason=f"Use {STREAM_PATH}")
            return

        logger.info("Pi client connected: %s", websocket.remote_address)
        try:
            async for message in websocket:
                self.counter.record(message)
        finally:
            logger.info("Pi client disconnected: %s", websocket.remote_address)


async def report_frame_counts(counter: FrameCounter, interval: float = 1.0) -> None:
    """Print per-frame totals at a fixed interval."""
    while True:
        await asyncio.sleep(interval)
        counts = counter.snapshot_and_reset()
        print(
            "frames/s "
            f"imu={counts['imu']} "
            f"audio={counts['audio']} "
            f"camera={counts['camera']}",
            flush=True,
        )


async def run_server(host: str = HOST, port: int = PORT) -> None:
    """Run the development receiver until it is interrupted."""
    server = DevelopmentWebSocketServer()
    reporter = asyncio.create_task(report_frame_counts(server.counter))
    try:
        async with serve(server.handle_connection, host, port, max_size=8 * 1024 * 1024):
            print(f"Development WebSocket server listening on ws://{host}:{port}{STREAM_PATH}")
            print("Outbound Pi commands are disabled.")
            await asyncio.Future()
    finally:
        reporter.cancel()
        await asyncio.gather(reporter, return_exceptions=True)


def parse_args() -> argparse.Namespace:
    """Parse optional local bind overrides."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=HOST, help=f"Bind host (default: {HOST})")
    parser.add_argument("--port", default=PORT, type=int, help=f"Bind port (default: {PORT})")
    return parser.parse_args()


def main() -> None:
    """Start the development server from the command line."""
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        asyncio.run(run_server(args.host, args.port))
    except KeyboardInterrupt:
        print("Development WebSocket server stopped.")


if __name__ == "__main__":
    main()

