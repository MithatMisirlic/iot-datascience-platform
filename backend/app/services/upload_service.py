"""Sensor-upload orchestration boundary."""

from pathlib import Path
from typing import BinaryIO

from sqlalchemy.orm import Session

from backend.app.crud import sensor_uploads as upload_crud
from backend.app.integrations.uploads import ArtifactStorage, DeferredUploadReceiver
from backend.app.models.sensor_upload import SensorUpload
from backend.app.services import exercise_service
from shared.enums import RecordingStatus, SensorFileType
from shared.errors import (
    InvalidArtifactError,
    ResourceConflictError,
    UnsupportedArtifactError,
)


_deferred_receiver = DeferredUploadReceiver()


def receive_sensor_upload(
    database: Session,
    exercise_id: str,
    file_type: SensorFileType,
    filename: str,
    content: BinaryIO,
    receiver: ArtifactStorage = _deferred_receiver,
) -> SensorUpload:
    """Validate, store, and persist metadata for a recording artifact."""

    exercise = exercise_service.get_exercise(database, exercise_id)
    if exercise.recordingStatus is not RecordingStatus.STOPPED or not exercise.hasData:
        raise ResourceConflictError(
            "Artifacts can only be uploaded after recording has stopped."
        )
    if not isinstance(file_type, SensorFileType):
        raise UnsupportedArtifactError("Artifact file type is not supported.")

    safe_filename = Path(filename).name
    if not safe_filename or safe_filename in {".", ".."}:
        raise InvalidArtifactError("Artifact filename is missing or invalid.")
    try:
        position = content.tell()
        first_byte = content.read(1)
        content.seek(position)
    except (AttributeError, OSError, TypeError, ValueError) as error:
        raise InvalidArtifactError("Artifact stream must be readable and seekable.") from error
    if not first_byte:
        raise InvalidArtifactError("Artifact file is empty.")

    storage_path = receiver.receive(
        exercise_id,
        file_type,
        safe_filename,
        content,
    )
    try:
        return upload_crud.create_sensor_upload(
            database,
            exercise_id,
            file_type,
            safe_filename,
            storage_path,
        )
    except Exception:
        receiver.delete(storage_path)
        database.rollback()
        raise
