"""Experiment endpoints declared by the API contract."""

from typing import Annotated

from fastapi import APIRouter, Body, Path, Query, status

from backend.app.api.responses import BAD_REQUEST, NOT_FOUND
from backend.app.api.v1.endpoints._placeholder import not_implemented
from backend.app.dependencies import DatabaseSession
from backend.app.schemas.experiment import Experiment, ExperimentInput, ExperimentPage


router = APIRouter(tags=["Experiments"])


@router.post(
    "/experiments",
    response_model=Experiment,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new experiment",
    description="Creates a new experiment. The server sets `id` and `createdAt`.",
    responses=BAD_REQUEST,
)
async def create_experiment(
    payload: Annotated[ExperimentInput, Body()],
    database: DatabaseSession,
) -> Experiment:
    """Create an experiment placeholder."""

    del payload, database
    not_implemented()


@router.get(
    "/experiments",
    response_model=ExperimentPage,
    summary="List experiments (paginated)",
)
async def list_experiments(
    database: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    pageSize: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ExperimentPage:
    """List experiments placeholder."""

    del database, page, pageSize
    not_implemented()


@router.get(
    "/experiments/{experimentId}",
    response_model=Experiment,
    summary="Get an experiment by id",
    responses=NOT_FOUND,
)
async def get_experiment(
    experimentId: Annotated[str, Path(description="The id of the experiment.")],
    database: DatabaseSession,
) -> Experiment:
    """Get an experiment placeholder."""

    del experimentId, database
    not_implemented()


@router.patch(
    "/experiments/{experimentId}",
    response_model=Experiment,
    summary="Update an experiment",
    description="Partially updates an experiment. Only provided fields are changed.",
    responses={**BAD_REQUEST, **NOT_FOUND},
)
async def update_experiment(
    experimentId: Annotated[str, Path(description="The id of the experiment.")],
    payload: Annotated[ExperimentInput, Body()],
    database: DatabaseSession,
) -> Experiment:
    """Update an experiment placeholder."""

    del experimentId, payload, database
    not_implemented()


@router.delete(
    "/experiments/{experimentId}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete an experiment and all related data",
    description=(
        "Deletes the experiment together with all its exercises and their "
        "recorded data."
    ),
    responses=NOT_FOUND,
)
async def delete_experiment(
    experimentId: Annotated[str, Path(description="The id of the experiment.")],
    database: DatabaseSession,
) -> None:
    """Delete an experiment placeholder."""

    del experimentId, database
    not_implemented()
