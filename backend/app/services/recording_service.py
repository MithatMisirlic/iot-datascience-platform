"""Recording lifecycle business rules."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.app.crud import exercises as exercise_crud
from backend.app.models.exercise import Exercise
from shared.enums import RecordingStatus
from shared.errors import ResourceConflictError, ResourceNotFoundError


def _require_exercise(database: Session, exercise_id: str) -> Exercise:
    """Return an exercise or raise the application not-found error."""

    exercise = exercise_crud.get_exercise(database, exercise_id)
    if exercise is None:
        raise ResourceNotFoundError("Exercise not found.")
    return exercise


def start_recording(database: Session, exercise_id: str) -> Exercise:
    """Move an eligible exercise into the recording state."""

    exercise = _require_exercise(database, exercise_id)
    if exercise.hasData:
        raise ResourceConflictError(
            "Exercise data must be cleared before recording again."
        )
    if exercise.recordingStatus is RecordingStatus.RECORDING:
        raise ResourceConflictError("Exercise is already recording.")

    exercise.recordingStatus = RecordingStatus.RECORDING
    exercise.recordingStartedAt = datetime.now(UTC)
    exercise.recordingEndedAt = None
    return exercise_crud.save_exercise(database, exercise)


def stop_recording(database: Session, exercise_id: str) -> Exercise:
    """Stop an active recording and mark raw data as available."""

    exercise = _require_exercise(database, exercise_id)
    if exercise.recordingStatus is not RecordingStatus.RECORDING:
        raise ResourceConflictError("Exercise is not currently recording.")

    exercise.recordingStatus = RecordingStatus.STOPPED
    exercise.recordingEndedAt = datetime.now(UTC)
    exercise.hasData = True
    return exercise_crud.save_exercise(database, exercise)
