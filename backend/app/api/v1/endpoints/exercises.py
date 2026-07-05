"""Exercise endpoints declared by the API contract."""

from typing import Annotated

from fastapi import APIRouter, Body, Path, Query, status

from backend.app.api.responses import BAD_REQUEST, NOT_FOUND
from backend.app.api.v1.endpoints._placeholder import not_implemented
from backend.app.dependencies import DatabaseSession
from backend.app.schemas.exercise import Exercise, ExerciseInput, ExercisePage


router = APIRouter(tags=["Exercises"])


@router.post(
    "/experiments/{experimentId}/exercises",
    response_model=Exercise,
    status_code=status.HTTP_201_CREATED,
    summary="Create an exercise within an experiment",
    description="Creates a new exercise. The server sets `id` and `createdAt`.",
    responses={**BAD_REQUEST, **NOT_FOUND},
)
async def create_exercise(
    experimentId: Annotated[str, Path(description="The id of the experiment.")],
    payload: Annotated[ExerciseInput, Body()],
    database: DatabaseSession,
) -> Exercise:
    """Create an exercise placeholder."""

    del experimentId, payload, database
    not_implemented()


@router.get(
    "/experiments/{experimentId}/exercises",
    response_model=list[Exercise],
    summary="List all exercises of an experiment",
    responses=NOT_FOUND,
)
async def list_experiment_exercises(
    experimentId: Annotated[str, Path(description="The id of the experiment.")],
    database: DatabaseSession,
) -> list[Exercise]:
    """List one experiment's exercises placeholder."""

    del experimentId, database
    not_implemented()


@router.get(
    "/exercises",
    response_model=ExercisePage,
    summary="List all exercises (across experiments, paginated)",
)
async def list_exercises(
    database: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    pageSize: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ExercisePage:
    """List all exercises placeholder."""

    del database, page, pageSize
    not_implemented()


@router.get(
    "/exercises/{exerciseId}",
    response_model=Exercise,
    summary="Get an exercise by id",
    responses=NOT_FOUND,
)
async def get_exercise(
    exerciseId: Annotated[str, Path(description="The id of the exercise.")],
    database: DatabaseSession,
) -> Exercise:
    """Get an exercise placeholder."""

    del exerciseId, database
    not_implemented()


@router.delete(
    "/exercises/{exerciseId}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete an exercise completely",
    responses=NOT_FOUND,
)
async def delete_exercise(
    exerciseId: Annotated[str, Path(description="The id of the exercise.")],
    database: DatabaseSession,
) -> None:
    """Delete an exercise placeholder."""

    del exerciseId, database
    not_implemented()
