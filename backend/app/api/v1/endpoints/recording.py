"""Recording-control endpoints declared by the API contract."""

from typing import Annotated

from fastapi import APIRouter, Path

from backend.app.api.responses import CONFLICT, NOT_FOUND
from backend.app.dependencies import DatabaseSession, RecordingBackendDependency
from backend.app.schemas.exercise import Exercise
from backend.app.services import recording_service


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
def start_recording(
    exerciseId: Annotated[str, Path(description="The id of the exercise.")],
    database: DatabaseSession,
    recording_backend: RecordingBackendDependency,
) -> Exercise:
    """Start recording for an eligible exercise."""

    return Exercise.model_validate(
        recording_service.start_recording(database, exerciseId, recording_backend)
    )


@router.post(
    "/exercises/{exerciseId}/recording/stop",
    response_model=Exercise,
    summary="Stop data recording for an exercise",
    responses={**NOT_FOUND, **CONFLICT},
)
def stop_recording(
    exerciseId: Annotated[str, Path(description="The id of the exercise.")],
    database: DatabaseSession,
    recording_backend: RecordingBackendDependency,
) -> Exercise:
    """Stop an active exercise recording."""

    return Exercise.model_validate(
        recording_service.stop_recording(database, exerciseId, recording_backend)
    )
