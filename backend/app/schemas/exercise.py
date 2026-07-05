"""Exercise request and response schemas from the API contract."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.experimental.missing_sentinel import MISSING

from backend.app.schemas.common import Properties
from shared.enums import RecordingStatus


class ExerciseInput(BaseModel):
    """Writable exercise fields."""

    properties: Properties | MISSING = MISSING


class Exercise(BaseModel):
    """Exercise returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    experimentId: str
    createdAt: datetime
    recordingStatus: RecordingStatus
    hasData: bool
    recordingStartedAt: datetime | None = None
    recordingEndedAt: datetime | None = None
    properties: Properties | MISSING = MISSING


class ExercisePage(BaseModel):
    """Paginated exercise response."""

    items: list[Exercise]
    page: int
    pageSize: int
    total: int
