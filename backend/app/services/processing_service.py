"""Raw-frame processing and ProcessedResult persistence use case."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from backend.app.crud import processed_results as result_crud
from backend.app.integrations.raw_frames import RawFrameStorage
from backend.app.schemas.exercise_data import ExerciseData
from backend.app.services import exercise_service
from pipeline.core.process_exercise import process_exercise as run_pipeline
from pipeline.core.processing_result import to_exercise_data
from shared.enums import RecordingStatus
from shared.errors import InvalidProcessedResultError, ResourceConflictError


def process_raw_exercise(
    database: Session,
    exercise_id: str,
    storage: RawFrameStorage,
) -> dict[str, Any]:
    """Process stored raw frames and atomically persist contract features."""
    exercise = exercise_service.get_exercise(database, exercise_id)
    if result_crud.get_exercise_result(database, exercise_id) is not None:
        raise ResourceConflictError("Exercise already has a processed result.")

    raw_frames = storage.load(exercise_id)
    generic_features = run_pipeline(
        raw_frames.imu,
        raw_frames.audio,
        raw_frames.mouth,
    )
    output = to_exercise_data(generic_features)
    try:
        contract_result = ExerciseData.model_validate(
            {
                **output,
                "exerciseId": exercise.id,
                "startedAt": exercise.recordingStartedAt,
                "endedAt": exercise.recordingEndedAt,
            }
        )
    except ValidationError as error:
        raise InvalidProcessedResultError(
            "Pipeline output does not match the ExerciseData contract."
        ) from error

    features = contract_result.model_dump(
        mode="json",
        exclude={"exerciseId", "startedAt", "endedAt"},
        exclude_unset=True,
    )
    if isinstance(output.get("metadata"), dict):
        features["metadata"] = output["metadata"]
    try:
        result = result_crud.stage_exercise_result(
            database,
            exercise.id,
            features,
        )
        exercise.hasData = True
        exercise.recordingStatus = RecordingStatus.STOPPED
        result_crud.commit_staged_result(database, result)
    except Exception:
        database.rollback()
        raise

    response = contract_result.model_dump(mode="json", exclude_unset=True)
    if isinstance(output.get("metadata"), dict):
        response["metadata"] = output["metadata"]
    return response
