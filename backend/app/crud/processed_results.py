"""Processed result persistence operations."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.models.processed_result import ProcessedResult


def create_exercise_result(
    database: Session,
    exercise_id: str,
    features: dict[str, object],
) -> ProcessedResult:
    """Persist one validated processed result for an exercise."""
    result = stage_exercise_result(database, exercise_id, features)
    return commit_staged_result(database, result)


def stage_exercise_result(
    database: Session,
    exercise_id: str,
    features: dict[str, object],
) -> ProcessedResult:
    """Stage and flush a result without committing its surrounding use case."""
    result = ProcessedResult(exercise_id=exercise_id, features=features)
    database.add(result)
    database.flush()
    return result


def commit_staged_result(database: Session, result: ProcessedResult) -> ProcessedResult:
    """Commit a staged result and all related state changes atomically."""
    try:
        database.commit()
        database.refresh(result)
    except Exception:
        database.rollback()
        raise
    return result


def get_exercise_result(
    database: Session,
    exercise_id: str,
) -> ProcessedResult | None:
    """Return the processed result associated with an exercise."""

    statement = select(ProcessedResult).where(
        ProcessedResult.exercise_id == exercise_id
    )
    return database.scalar(statement)


def delete_exercise_result(database: Session, exercise_id: str) -> None:
    """Stage deletion of an exercise's processed result, if present."""

    database.execute(
        delete(ProcessedResult).where(ProcessedResult.exercise_id == exercise_id)
    )
