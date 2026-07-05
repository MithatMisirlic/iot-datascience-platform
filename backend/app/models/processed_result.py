"""Processed result database model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.exercise import Exercise


class ProcessedResult(Base):
    """Internal feature data produced for exactly one exercise."""

    __tablename__ = "processed_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    exercise_id: Mapped[str] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    features: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    exercise: Mapped[Exercise] = relationship(
        back_populates="processed_result"
    )
