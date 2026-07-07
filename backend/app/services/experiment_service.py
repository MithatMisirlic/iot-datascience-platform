"""Experiment application use cases."""

from sqlalchemy.orm import Session

from backend.app.crud import experiments as experiment_crud
from backend.app.integrations.uploads import ArtifactStorage
from backend.app.models.experiment import Experiment
from backend.app.schemas.experiment import ExperimentInput
from backend.app.services import artifact_service
from shared.errors import ResourceNotFoundError


def create_experiment(database: Session, payload: ExperimentInput) -> Experiment:
    """Create and return an experiment."""

    return experiment_crud.create_experiment(database, payload)


def list_experiments(
    database: Session,
    page: int,
    page_size: int,
) -> tuple[list[Experiment], int]:
    """Return one page of experiments and the total count."""

    return experiment_crud.list_experiments(database, page, page_size)


def get_experiment(database: Session, experiment_id: str) -> Experiment:
    """Return an experiment or raise an application not-found error."""

    experiment = experiment_crud.get_experiment(database, experiment_id)
    if experiment is None:
        raise ResourceNotFoundError("Experiment not found.")
    return experiment


def update_experiment(
    database: Session,
    experiment_id: str,
    payload: ExperimentInput,
) -> Experiment:
    """Partially update an existing experiment."""

    experiment = get_experiment(database, experiment_id)
    return experiment_crud.update_experiment(database, experiment, payload)


def delete_experiment(
    database: Session,
    experiment_id: str,
    storage: ArtifactStorage,
) -> None:
    """Delete an experiment and its database-owned children."""

    experiment = get_experiment(database, experiment_id)
    artifact_service.delete_experiment_artifacts(database, experiment_id, storage)
    experiment_crud.delete_experiment(database, experiment)
