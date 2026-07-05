"""Experiment database model aligned with the public API contract."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, Float, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

if TYPE_CHECKING:
    from backend.app.models.exercise import Exercise


class Experiment(Base):
    """Test-person metadata and its collection of exercises."""

    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    patientNumber: Mapped[str | None] = mapped_column(String(128), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    properties: Mapped[dict[str, str]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    createdAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    exercises: Mapped[list[Exercise]] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
