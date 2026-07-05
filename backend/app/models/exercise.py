"""Exercise database model aligned with the public API contract."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from shared.enums import RecordingStatus

if TYPE_CHECKING:
    from backend.app.models.experiment import Experiment
    from backend.app.models.processed_result import ProcessedResult
    from backend.app.models.sensor_upload import SensorUpload


class Exercise(Base):
    """One recordable exercise belonging to an experiment."""

    __tablename__ = "exercises"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    experimentId: Mapped[str] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    createdAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    recordingStatus: Mapped[RecordingStatus] = mapped_column(
        SqlEnum(
            RecordingStatus,
            name="recording_status",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum_type: [item.value for item in enum_type],
        ),
        default=RecordingStatus.IDLE,
        server_default=RecordingStatus.IDLE.value,
        nullable=False,
    )
    hasData: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )
    recordingStartedAt: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    recordingEndedAt: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    properties: Mapped[dict[str, str]] = mapped_column(
        JSON, default=dict, nullable=False
    )

    experiment: Mapped[Experiment] = relationship(back_populates="exercises")
    sensor_uploads: Mapped[list[SensorUpload]] = relationship(
        back_populates="exercise",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    processed_result: Mapped[ProcessedResult | None] = relationship(
        back_populates="exercise",
        cascade="all, delete-orphan",
        passive_deletes=True,
        single_parent=True,
        uselist=False,
    )
