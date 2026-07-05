"""Experiment request and response schemas from the API contract."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.experimental.missing_sentinel import MISSING

from backend.app.schemas.common import Properties


class ExperimentInput(BaseModel):
    """Writable experiment fields."""

    patientNumber: str | MISSING = MISSING
    height: float | MISSING = MISSING
    age: int | MISSING = MISSING
    weight: float | MISSING = MISSING
    properties: Properties | MISSING = MISSING


class Experiment(ExperimentInput):
    """Experiment returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    createdAt: datetime


class ExperimentPage(BaseModel):
    """Paginated experiment response."""

    items: list[Experiment]
    page: int
    pageSize: int
    total: int
