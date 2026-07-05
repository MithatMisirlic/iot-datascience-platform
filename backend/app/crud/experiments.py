"""Experiment persistence operations."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.experiment import Experiment
from backend.app.schemas.experiment import ExperimentInput


def create_experiment(database: Session, payload: ExperimentInput) -> Experiment:
    """Persist and return a new experiment."""

    experiment = Experiment(**payload.model_dump(exclude_unset=True))
    database.add(experiment)
    database.commit()
    database.refresh(experiment)
    return experiment


def list_experiments(
    database: Session,
    page: int,
    page_size: int,
) -> tuple[list[Experiment], int]:
    """Return one deterministic page of experiments and the total count."""

    total = database.scalar(select(func.count()).select_from(Experiment)) or 0
    statement = (
        select(Experiment)
        .order_by(Experiment.createdAt, Experiment.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(database.scalars(statement).all()), total


def get_experiment(database: Session, experiment_id: str) -> Experiment | None:
    """Return an experiment by id, if it exists."""

    return database.get(Experiment, experiment_id)


def update_experiment(
    database: Session,
    experiment: Experiment,
    payload: ExperimentInput,
) -> Experiment:
    """Apply provided fields to an existing experiment."""

    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(experiment, field_name, value)
    database.commit()
    database.refresh(experiment)
    return experiment


def delete_experiment(database: Session, experiment: Experiment) -> None:
    """Delete an experiment and its database-owned children."""

    database.delete(experiment)
    database.commit()
