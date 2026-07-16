"""Recording lifecycle business rules."""

from datetime import UTC, datetime
import logging

from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.integrations.raw_frames import (
    LocalJsonRawFrameStorage,
    RawExerciseFrames,
)
from backend.app.integrations.recording import RecordingBackend
from backend.app.models.exercise import Exercise
from backend.app.services import exercise_service, processing_service
from backend.app.services.live_recording_session import live_recording_manager
from shared.enums import RecordingStatus
from shared.errors import ResourceConflictError


logger = logging.getLogger(__name__)


def start_recording(
    database: Session,
    exercise_id: str,
    recording_backend: RecordingBackend,
) -> Exercise:
    """Move an eligible exercise into the recording state."""

    exercise = exercise_service.get_exercise(database, exercise_id)
    if exercise.hasData:
        raise ResourceConflictError(
            "Exercise data must be cleared before recording again."
        )
    if exercise.recordingStatus is RecordingStatus.RECORDING:
        raise ResourceConflictError("Exercise is already recording.")

    recording_backend.start_recording(exercise.id)
    exercise.recordingStatus = RecordingStatus.RECORDING
    exercise.recordingStartedAt = datetime.now(UTC)
    exercise.recordingEndedAt = None
    saved = exercise_service.save_exercise(database, exercise)

    storage = LocalJsonRawFrameStorage(settings.resolved_raw_frame_dir)
    storage.save(exercise.id, RawExerciseFrames())
    live_recording_manager.start_recording(exercise.id)
    return saved


def stop_recording(
    database: Session,
    exercise_id: str,
    recording_backend: RecordingBackend,
) -> Exercise:
    """Stop an active recording and mark raw data as available."""

    exercise = exercise_service.get_exercise(database, exercise_id)
    if exercise.recordingStatus is not RecordingStatus.RECORDING:
        raise ResourceConflictError("Exercise is not currently recording.")

    recording_backend.stop_recording(exercise.id)
    exercise.recordingStatus = RecordingStatus.STOPPED
    exercise.recordingEndedAt = datetime.now(UTC)
    exercise.hasData = True
    saved = exercise_service.save_exercise(database, exercise)

    storage = LocalJsonRawFrameStorage(settings.resolved_raw_frame_dir)
    raw_frames = live_recording_manager.stop_recording(exercise.id)
    storage.save(exercise.id, raw_frames)
    try:
        processing_service.process_raw_exercise(database, exercise.id, storage)
    except Exception as error:
        live_recording_manager.mark_error(str(error))
        logger.exception(
            "Recording stopped but automatic processing failed for exercise %s",
            exercise.id,
        )
        raise ResourceConflictError(
            "Recording stopped, but automatic processing failed. Raw data was retained."
        ) from error

    live_recording_manager.mark_results_ready()
    return saved
