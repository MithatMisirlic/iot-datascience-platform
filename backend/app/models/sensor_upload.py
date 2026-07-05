"""Sensor upload database model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from shared.enums import SensorFileType

if TYPE_CHECKING:
    from backend.app.models.exercise import Exercise


class SensorUpload(Base):
    """Internal metadata for one sensor file uploaded for an exercise."""

    __tablename__ = "sensor_uploads"

    id: Mapped[int] = mapped_column(primary_key=True)
    exercise_id: Mapped[str] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    file_type: Mapped[SensorFileType] = mapped_column(
        SqlEnum(
            SensorFileType,
            name="sensor_file_type",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda enum_type: [item.value for item in enum_type],
        ),
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    exercise: Mapped[Exercise] = relationship(
        back_populates="sensor_uploads"
    )
