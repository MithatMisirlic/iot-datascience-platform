"""Artifact cleanup orchestration shared by parent delete flows."""

from collections.abc import Iterable

from sqlalchemy.orm import Session

from backend.app.crud import sensor_uploads as upload_crud
from backend.app.integrations.uploads import ArtifactStorage
from backend.app.models.sensor_upload import SensorUpload


def _delete_stored_files(
    uploads: Iterable[SensorUpload],
    storage: ArtifactStorage,
) -> None:
    """Delete physical files represented by upload metadata rows."""

    for upload in uploads:
        storage.delete(upload.file_path)


def delete_exercise_artifacts(
    database: Session,
    exercise_id: str,
    storage: ArtifactStorage,
) -> None:
    """Delete stored files and stage metadata deletion for an exercise."""

    uploads = upload_crud.list_exercise_uploads(database, exercise_id)
    _delete_stored_files(uploads, storage)
    upload_crud.delete_exercise_uploads(database, exercise_id)


def delete_experiment_artifacts(
    database: Session,
    experiment_id: str,
    storage: ArtifactStorage,
) -> None:
    """Delete stored files for all exercises in an experiment."""

    uploads = upload_crud.list_experiment_uploads(database, experiment_id)
    _delete_stored_files(uploads, storage)
