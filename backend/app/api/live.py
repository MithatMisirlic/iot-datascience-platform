"""WebSocket endpoints for Pi streaming and frontend live state."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.services.live_recording_session import live_recording_manager


logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/stream")
async def pi_stream(websocket: WebSocket) -> None:
    """Receive existing Pi JSON frames without changing the Pi contract."""
    await websocket.accept()
    live_recording_manager.mark_pi_connected()
    try:
        while True:
            message = await websocket.receive_text()
            try:
                frame = json.loads(message)
            except json.JSONDecodeError:
                logger.warning("Ignoring malformed Pi WebSocket frame")
                continue
            if isinstance(frame, dict):
                live_recording_manager.receive_frame(frame)
    except WebSocketDisconnect:
        live_recording_manager.mark_pi_disconnected()
    except Exception:
        live_recording_manager.mark_pi_disconnected()
        logger.exception("Pi stream WebSocket failed")
        raise


@router.websocket("/ws")
async def live_state(websocket: WebSocket) -> None:
    """Broadcast lightweight live state to dashboard clients."""
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(live_recording_manager.snapshot())
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        return
