"""Exercise application use cases."""

from sqlalchemy.orm import Session

from backend.app.crud import exercises as exercise_crud
from backend.app.integrations.uploads import ArtifactStorage
from backend.app.models.exercise import Exercise
from backend.app.schemas.exercise import ExerciseInput
from backend.app.services import artifact_service
from backend.app.services import experiment_service
from shared.errors import ResourceNotFoundError


def create_exercise(
    database: Session,
    experiment_id: str,
    payload: ExerciseInput,
) -> Exercise:
    """Create an exercise under an existing experiment."""

    experiment_service.get_experiment(database, experiment_id)
    return exercise_crud.create_exercise(database, experiment_id, payload)


def list_experiment_exercises(
    database: Session,
    experiment_id: str,
) -> list[Exercise]:
    """Return all exercises owned by an existing experiment."""

    experiment_service.get_experiment(database, experiment_id)
    return exercise_crud.list_experiment_exercises(database, experiment_id)


def list_exercises(
    database: Session,
    page: int,
    page_size: int,
) -> tuple[list[Exercise], int]:
    """Return one page of exercises and the total count."""

    return exercise_crud.list_exercises(database, page, page_size)


def get_exercise(database: Session, exercise_id: str) -> Exercise:
    """Return an exercise or raise an application not-found error."""

    exercise = exercise_crud.get_exercise(database, exercise_id)
    if exercise is None:
        raise ResourceNotFoundError("Exercise not found.")
    return exercise


def save_exercise(database: Session, exercise: Exercise) -> Exercise:
    """Persist state changes to an exercise."""

    return exercise_crud.save_exercise(database, exercise)


def delete_exercise(
    database: Session,
    exercise_id: str,
    storage: ArtifactStorage,
) -> None:
    """Delete an exercise and its database-owned children."""

    exercise = get_exercise(database, exercise_id)
    artifact_service.delete_exercise_artifacts(database, exercise_id, storage)
    exercise_crud.delete_exercise(database, exercise)
