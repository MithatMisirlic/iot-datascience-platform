"""Recording-control endpoints declared by the API contract."""

from typing import Annotated

from fastapi import APIRouter, Path

from backend.app.api.responses import CONFLICT, NOT_FOUND
from backend.app.api.v1.endpoints._placeholder import not_implemented
from backend.app.dependencies import DatabaseSession
from backend.app.schemas.exercise import Exercise


router = APIRouter(tags=["Recording"])


@router.post(
    "/exercises/{exerciseId}/recording/start",
    response_model=Exercise,
    summary="Start data recording for an exercise",
    description=(
        "Starts recording. Only works if the exercise has no data yet; otherwise "
        "`409 Conflict` is returned. Clear the data first to re-record."
    ),
    responses={**NOT_FOUND, **CONFLICT},
)
async def start_recording(
    exerciseId: Annotated[str, Path(description="The id of the exercise.")],
    database: DatabaseSession,
) -> Exercise:
    """Start recording placeholder."""

    del exerciseId, database
    not_implemented()


@router.post(
    "/exercises/{exerciseId}/recording/stop",
    response_model=Exercise,
    summary="Stop data recording for an exercise",
    responses={**NOT_FOUND, **CONFLICT},
)
async def stop_recording(
    exerciseId: Annotated[str, Path(description="The id of the exercise.")],
    database: DatabaseSession,
) -> Exercise:
    """Stop recording placeholder."""

    del exerciseId, database
    not_implemented()
