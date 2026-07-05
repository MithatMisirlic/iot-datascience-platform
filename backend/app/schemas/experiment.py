"""Experiment request and response schemas from the API contract."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator
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

    @model_validator(mode="before")
    @classmethod
    def omit_unset_database_values(cls, value: Any) -> Any:
        """Omit null database values for optional, non-nullable API fields."""

        if not hasattr(value, "id"):
            return value
        data = {
            "id": value.id,
            "createdAt": value.createdAt,
            "properties": value.properties,
        }
        for field_name in ("patientNumber", "height", "age", "weight"):
            field_value = getattr(value, field_name)
            if field_value is not None:
                data[field_name] = field_value
        return data


class ExperimentPage(BaseModel):
    """Paginated experiment response."""

    items: list[Experiment]
    page: int
    pageSize: int
    total: int
