"""Exercise-data endpoints declared by the API contract."""

from typing import Annotated

from fastapi import APIRouter, Path, status

from backend.app.api.responses import NOT_FOUND
from backend.app.dependencies import DatabaseSession
from backend.app.schemas.common import Error
from backend.app.schemas.exercise_data import ExerciseData
from backend.app.services import exercise_data_service


router = APIRouter(tags=["Data"])


@router.get(
    "/exercises/{exerciseId}/data",
    response_model=ExerciseData,
    summary="Get recorded and processed data for an exercise",
    responses={
        404: {
            "model": Error,
            "description": "Exercise not found, or the exercise has no data yet.",
        }
    },
)
def get_exercise_data(
    exerciseId: Annotated[str, Path(description="The id of the exercise.")],
    database: DatabaseSession,
) -> ExerciseData:
    """Return processed data for an exercise."""

    return exercise_data_service.get_exercise_data(database, exerciseId)


@router.delete(
    "/exercises/{exerciseId}/data",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Clear recorded exercise data",
    description=(
        "Removes the recorded data but keeps the exercise, allowing a new recording."
    ),
    responses=NOT_FOUND,
)
def clear_exercise_data(
    exerciseId: Annotated[str, Path(description="The id of the exercise.")],
    database: DatabaseSession,
) -> None:
    """Clear exercise data and reset its recording state."""

    exercise_data_service.clear_exercise_data(database, exerciseId)
    return None
