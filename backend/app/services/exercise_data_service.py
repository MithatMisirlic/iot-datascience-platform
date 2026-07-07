"""Exercise-data retrieval and clearing business rules."""

from sqlalchemy.orm import Session

from backend.app.crud import processed_results as result_crud
from backend.app.integrations.uploads import ArtifactStorage
from backend.app.schemas.exercise_data import ExerciseData
from backend.app.services import artifact_service, exercise_service
from shared.enums import RecordingStatus
from shared.errors import ResourceNotFoundError


def get_exercise_data(database: Session, exercise_id: str) -> ExerciseData:
    """Map stored processed JSON into the public exercise-data schema."""

    exercise = exercise_service.get_exercise(database, exercise_id)
    if not exercise.hasData:
        raise ResourceNotFoundError("Exercise has no recorded data.")

    result = result_crud.get_exercise_result(database, exercise_id)
    if result is None:
        raise ResourceNotFoundError("Processed exercise data is not available.")

    payload = dict(result.features)
    payload.update(
        exerciseId=exercise.id,
        startedAt=exercise.recordingStartedAt,
        endedAt=exercise.recordingEndedAt,
    )
    return ExerciseData.model_validate(payload)


def clear_exercise_data(
    database: Session,
    exercise_id: str,
    storage: ArtifactStorage,
) -> None:
    """Remove internal data and reset an exercise for another recording."""

    exercise = exercise_service.get_exercise(database, exercise_id)

    artifact_service.delete_exercise_artifacts(database, exercise_id, storage)
    result_crud.delete_exercise_result(database, exercise_id)
    exercise.hasData = False
    exercise.recordingStatus = RecordingStatus.IDLE
    exercise.recordingStartedAt = None
    exercise.recordingEndedAt = None
    exercise_service.save_exercise(database, exercise)
