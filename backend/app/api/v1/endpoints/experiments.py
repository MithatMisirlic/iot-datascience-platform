"""Experiment endpoints declared by the API contract."""

from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Path, Query, status

from backend.app.api.responses import BAD_REQUEST, NOT_FOUND
from backend.app.crud import experiments as experiment_crud
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
def create_experiment(
    payload: Annotated[ExperimentInput, Body()],
    database: DatabaseSession,
) -> Experiment:
    """Create and persist an experiment."""

    return Experiment.model_validate(
        experiment_crud.create_experiment(database, payload)
    )


@router.get(
    "/experiments",
    response_model=ExperimentPage,
    summary="List experiments (paginated)",
)
def list_experiments(
    database: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    pageSize: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ExperimentPage:
    """List a page of experiments."""

    items, total = experiment_crud.list_experiments(database, page, pageSize)
    return ExperimentPage(
        items=[Experiment.model_validate(item) for item in items],
        page=page,
        pageSize=pageSize,
        total=total,
    )


@router.get(
    "/experiments/{experimentId}",
    response_model=Experiment,
    summary="Get an experiment by id",
    responses=NOT_FOUND,
)
def get_experiment(
    experimentId: Annotated[str, Path(description="The id of the experiment.")],
    database: DatabaseSession,
) -> Experiment:
    """Get an experiment by id."""

    experiment = experiment_crud.get_experiment(database, experimentId)
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    return Experiment.model_validate(experiment)


@router.patch(
    "/experiments/{experimentId}",
    response_model=Experiment,
    summary="Update an experiment",
    description="Partially updates an experiment. Only provided fields are changed.",
    responses={**BAD_REQUEST, **NOT_FOUND},
)
def update_experiment(
    experimentId: Annotated[str, Path(description="The id of the experiment.")],
    payload: Annotated[ExperimentInput, Body()],
    database: DatabaseSession,
) -> Experiment:
    """Partially update an experiment."""

    experiment = experiment_crud.get_experiment(database, experimentId)
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    return Experiment.model_validate(
        experiment_crud.update_experiment(database, experiment, payload)
    )


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
def delete_experiment(
    experimentId: Annotated[str, Path(description="The id of the experiment.")],
    database: DatabaseSession,
) -> None:
    """Delete an experiment and all related records."""

    experiment = experiment_crud.get_experiment(database, experimentId)
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    experiment_crud.delete_experiment(database, experiment)
    return None
