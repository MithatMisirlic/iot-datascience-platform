"""Processed-result production use cases."""

from pydantic import ValidationError
from sqlalchemy.orm import Session

from backend.app.crud import processed_results as result_crud
from backend.app.crud import sensor_uploads as upload_crud
from backend.app.integrations.processing import (
    DeferredResultProcessor,
    ProcessingArtifact,
    ResultProcessor,
)
from backend.app.models.processed_result import ProcessedResult
from backend.app.schemas.exercise_data import ExerciseData
from backend.app.services import exercise_service
from shared.enums import RecordingStatus
from shared.errors import (
    InvalidProcessedResultError,
    MissingArtifactsError,
    ResourceConflictError,
)


_deferred_processor = DeferredResultProcessor()


def process_exercise(
    database: Session,
    exercise_id: str,
    processor: ResultProcessor = _deferred_processor,
) -> ProcessedResult:
    """Validate inputs, delegate processing, and persist a valid result."""

    exercise = exercise_service.get_exercise(database, exercise_id)
    if exercise.recordingStatus is not RecordingStatus.STOPPED:
        raise ResourceConflictError(
            "Exercise processing requires a stopped recording."
        )
    if result_crud.get_exercise_result(database, exercise_id) is not None:
        raise ResourceConflictError("Exercise already has a processed result.")

    uploads = upload_crud.list_exercise_uploads(database, exercise_id)
    available_types = {upload.file_type for upload in uploads}
    missing_types = processor.required_file_types - available_types
    if missing_types:
        missing_names = ", ".join(sorted(file_type.value for file_type in missing_types))
        raise MissingArtifactsError(f"Missing required artifacts: {missing_names}.")

    artifacts = tuple(
        ProcessingArtifact(
            file_type=upload.file_type,
            original_filename=upload.original_filename,
            storage_path=upload.file_path,
        )
        for upload in uploads
    )
    output = processor.process(exercise_id, artifacts)
    if not isinstance(output, dict):
        raise InvalidProcessedResultError(
            "Processor output must be a JSON object."
        )

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
            "Processor output does not match the ExerciseData contract."
        ) from error

    features = contract_result.model_dump(
        mode="json",
        exclude={"exerciseId", "startedAt", "endedAt"},
        exclude_unset=True,
    )
    if isinstance(output.get("metadata"), dict):
        features["metadata"] = output["metadata"]
    return result_crud.create_exercise_result(database, exercise_id, features)
