"""Recorded and processed exercise-data schemas from the API contract."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field
from pydantic.experimental.missing_sentinel import MISSING


class SignalFloat(BaseModel):
    """One-dimensional floating-point signal channel."""

    values: list[float]
    sampleRate: float
    unit: str | MISSING = MISSING


SamplePair = Annotated[list[float], Field(min_length=2, max_length=2)]


class MouthOpening(BaseModel):
    """Relative vertical and horizontal mouth-opening samples."""

    values: list[SamplePair]
    sampleRate: float


class SoundPressure(SignalFloat):
    """Sound-pressure signal in Pascal or Decibel."""

    unit: Literal["Pa", "dB"] | MISSING = MISSING


class FootSpeed(SignalFloat):
    """Foot-speed signal in centimeters per second."""

    unit: Literal["cm/s"] | MISSING = MISSING


class StepLengths(BaseModel):
    """Processed step lengths in centimeters."""

    values: list[float] | MISSING = MISSING
    unit: Literal["cm"] | MISSING = MISSING


class AggregateStats(BaseModel):
    """Per-signal scalar average or median values."""

    mouthOpeningVertical: float | MISSING = MISSING
    mouthOpeningHorizontal: float | MISSING = MISSING
    soundPressure: float | MISSING = MISSING
    footSpeed: float | MISSING = MISSING
    stepLength: float | MISSING = MISSING


class Aggregates(BaseModel):
    """Processed aggregate results."""

    stepLengths: StepLengths | MISSING = MISSING
    averages: AggregateStats | MISSING = MISSING
    medians: AggregateStats | MISSING = MISSING


class ExerciseData(BaseModel):
    """Recorded and processed data for one exercise."""

    exerciseId: str
    startedAt: datetime | None = None
    endedAt: datetime | None = None
    mouthOpening: MouthOpening
    soundPressure: SoundPressure
    footSpeed: FootSpeed
    aggregates: Aggregates
