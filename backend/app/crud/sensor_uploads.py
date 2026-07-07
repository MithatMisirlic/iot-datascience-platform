"""Sensor upload persistence operations."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.models.exercise import Exercise
from backend.app.models.sensor_upload import SensorUpload
from shared.enums import SensorFileType


def create_sensor_upload(
    database: Session,
    exercise_id: str,
    file_type: SensorFileType,
    original_filename: str,
    file_path: str,
) -> SensorUpload:
    """Persist metadata for one stored recording artifact."""

    upload = SensorUpload(
        exercise_id=exercise_id,
        file_type=file_type,
        original_filename=original_filename,
        file_path=file_path,
    )
    database.add(upload)
    database.commit()
    database.refresh(upload)
    return upload


def list_exercise_uploads(
    database: Session,
    exercise_id: str,
) -> list[SensorUpload]:
    """Return all artifact metadata rows for an exercise."""

    statement = (
        select(SensorUpload)
        .where(SensorUpload.exercise_id == exercise_id)
        .order_by(SensorUpload.file_type, SensorUpload.id)
    )
    return list(database.scalars(statement).all())


def list_experiment_uploads(
    database: Session,
    experiment_id: str,
) -> list[SensorUpload]:
    """Return artifact metadata for every exercise in an experiment."""

    statement = (
        select(SensorUpload)
        .join(Exercise, SensorUpload.exercise_id == Exercise.id)
        .where(Exercise.experimentId == experiment_id)
    )
    return list(database.scalars(statement).all())


def delete_exercise_uploads(database: Session, exercise_id: str) -> None:
    """Stage deletion of every sensor upload owned by an exercise."""

    database.execute(
        delete(SensorUpload).where(SensorUpload.exercise_id == exercise_id)
    )
