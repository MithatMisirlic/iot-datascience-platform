"""Sensor upload persistence operations."""

from sqlalchemy import delete
from sqlalchemy.orm import Session

from backend.app.models.sensor_upload import SensorUpload


def delete_exercise_uploads(database: Session, exercise_id: str) -> None:
    """Stage deletion of every sensor upload owned by an exercise."""

    database.execute(
        delete(SensorUpload).where(SensorUpload.exercise_id == exercise_id)
    )
