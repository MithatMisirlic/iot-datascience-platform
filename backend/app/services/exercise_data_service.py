"""Exercise-data retrieval and clearing business rules."""

from sqlalchemy.orm import Session

from backend.app.crud import exercises as exercise_crud
from backend.app.crud import processed_results as result_crud
from backend.app.crud import sensor_uploads as upload_crud
from backend.app.schemas.exercise_data import ExerciseData
from shared.enums import RecordingStatus
from shared.errors import ResourceNotFoundError


def get_exercise_data(database: Session, exercise_id: str) -> ExerciseData:
    """Map stored processed JSON into the public exercise-data schema."""

    exercise = exercise_crud.get_exercise(database, exercise_id)
    if exercise is None:
        raise ResourceNotFoundError("Exercise not found.")
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


def clear_exercise_data(database: Session, exercise_id: str) -> None:
    """Remove internal data and reset an exercise for another recording."""

    exercise = exercise_crud.get_exercise(database, exercise_id)
    if exercise is None:
        raise ResourceNotFoundError("Exercise not found.")

    upload_crud.delete_exercise_uploads(database, exercise_id)
    result_crud.delete_exercise_result(database, exercise_id)
    exercise.hasData = False
    exercise.recordingStatus = RecordingStatus.IDLE
    exercise.recordingStartedAt = None
    exercise.recordingEndedAt = None
    exercise_crud.save_exercise(database, exercise)
