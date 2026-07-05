"""Exercise-data endpoints declared by the API contract."""

from typing import Annotated

from fastapi import APIRouter, Path, status

from backend.app.api.responses import NOT_FOUND
from backend.app.api.v1.endpoints._placeholder import not_implemented
from backend.app.dependencies import DatabaseSession
from backend.app.schemas.common import Error
from backend.app.schemas.exercise_data import ExerciseData


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
async def get_exercise_data(
    exerciseId: Annotated[str, Path(description="The id of the exercise.")],
    database: DatabaseSession,
) -> ExerciseData:
    """Get exercise data placeholder."""

    del exerciseId, database
    not_implemented()


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
async def clear_exercise_data(
    exerciseId: Annotated[str, Path(description="The id of the exercise.")],
    database: DatabaseSession,
) -> None:
    """Clear exercise data placeholder."""

    del exerciseId, database
    not_implemented()
