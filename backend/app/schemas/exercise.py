"""Exercise request and response schemas from the API contract."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, field_validator
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

    @field_validator(
        "createdAt",
        "recordingStartedAt",
        "recordingEndedAt",
        mode="after",
    )
    @classmethod
    def normalize_utc(cls, value: datetime | None) -> datetime | None:
        """Represent SQLite timestamps explicitly as UTC."""

        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class ExercisePage(BaseModel):
    """Paginated exercise response."""

    items: list[Exercise]
    page: int
    pageSize: int
    total: int
