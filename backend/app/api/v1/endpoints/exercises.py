"""Exercise endpoints declared by the API contract."""

from typing import Annotated

from fastapi import APIRouter, Body, Path, Query, status

from backend.app.api.responses import BAD_REQUEST, NOT_FOUND
from backend.app.dependencies import ArtifactStorageDependency, DatabaseSession
from backend.app.schemas.exercise import Exercise, ExerciseInput, ExercisePage
from backend.app.services import exercise_service


router = APIRouter(tags=["Exercises"])


@router.post(
    "/experiments/{experimentId}/exercises",
    response_model=Exercise,
    status_code=status.HTTP_201_CREATED,
    summary="Create an exercise within an experiment",
    description="Creates a new exercise. The server sets `id` and `createdAt`.",
    responses={**BAD_REQUEST, **NOT_FOUND},
)
def create_exercise(
    experimentId: Annotated[str, Path(description="The id of the experiment.")],
    payload: Annotated[ExerciseInput, Body()],
    database: DatabaseSession,
) -> Exercise:
    """Create an exercise under an existing experiment."""

    return Exercise.model_validate(
        exercise_service.create_exercise(database, experimentId, payload)
    )


@router.get(
    "/experiments/{experimentId}/exercises",
    response_model=list[Exercise],
    summary="List all exercises of an experiment",
    responses=NOT_FOUND,
)
def list_experiment_exercises(
    experimentId: Annotated[str, Path(description="The id of the experiment.")],
    database: DatabaseSession,
) -> list[Exercise]:
    """List all exercises belonging to an experiment."""

    return [
        Exercise.model_validate(item)
        for item in exercise_service.list_experiment_exercises(database, experimentId)
    ]


@router.get(
    "/exercises",
    response_model=ExercisePage,
    summary="List all exercises (across experiments, paginated)",
)
def list_exercises(
    database: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    pageSize: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ExercisePage:
    """List a page of exercises across all experiments."""

    items, total = exercise_service.list_exercises(database, page, pageSize)
    return ExercisePage(
        items=[Exercise.model_validate(item) for item in items],
        page=page,
        pageSize=pageSize,
        total=total,
    )


@router.get(
    "/exercises/{exerciseId}",
    response_model=Exercise,
    summary="Get an exercise by id",
    responses=NOT_FOUND,
)
def get_exercise(
    exerciseId: Annotated[str, Path(description="The id of the exercise.")],
    database: DatabaseSession,
) -> Exercise:
    """Get an exercise by id."""

    return Exercise.model_validate(
        exercise_service.get_exercise(database, exerciseId)
    )


@router.delete(
    "/exercises/{exerciseId}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete an exercise completely",
    responses=NOT_FOUND,
)
def delete_exercise(
    exerciseId: Annotated[str, Path(description="The id of the exercise.")],
    database: DatabaseSession,
    storage: ArtifactStorageDependency,
) -> None:
    """Delete an exercise and its related records."""

    exercise_service.delete_exercise(database, exerciseId, storage)
    return None
