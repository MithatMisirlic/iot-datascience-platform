"""Exercise persistence operations."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.exercise import Exercise
from backend.app.schemas.exercise import ExerciseInput


def create_exercise(
    database: Session,
    experiment_id: str,
    payload: ExerciseInput,
) -> Exercise:
    """Persist and return an exercise owned by an experiment."""

    exercise = Exercise(
        experimentId=experiment_id,
        **payload.model_dump(exclude_unset=True),
    )
    database.add(exercise)
    database.commit()
    database.refresh(exercise)
    return exercise


def list_experiment_exercises(
    database: Session,
    experiment_id: str,
) -> list[Exercise]:
    """Return all exercises belonging to one experiment."""

    statement = (
        select(Exercise)
        .where(Exercise.experimentId == experiment_id)
        .order_by(Exercise.createdAt, Exercise.id)
    )
    return list(database.scalars(statement).all())


def list_exercises(
    database: Session,
    page: int,
    page_size: int,
) -> tuple[list[Exercise], int]:
    """Return one deterministic page of exercises and the total count."""

    total = database.scalar(select(func.count()).select_from(Exercise)) or 0
    statement = (
        select(Exercise)
        .order_by(Exercise.createdAt, Exercise.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(database.scalars(statement).all()), total


def get_exercise(database: Session, exercise_id: str) -> Exercise | None:
    """Return an exercise by id, if it exists."""

    return database.get(Exercise, exercise_id)


def save_exercise(database: Session, exercise: Exercise) -> Exercise:
    """Commit pending changes to an exercise and return it."""

    database.add(exercise)
    database.commit()
    return exercise


def delete_exercise(database: Session, exercise: Exercise) -> None:
    """Delete an exercise and its database-owned children."""

    database.delete(exercise)
    database.commit()
