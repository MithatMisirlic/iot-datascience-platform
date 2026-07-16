"""Deterministic statistical helpers shared by sensor processors."""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence


def duration_seconds(timestamps: Sequence[float]) -> float:
    """Return the elapsed timestamp range, or zero for insufficient data."""
    if len(timestamps) < 2:
        return 0.0
    return max(0.0, max(timestamps) - min(timestamps))


def sample_rate_estimate_hz(timestamps: Sequence[float]) -> float:
    """Estimate rate from sample intervals across the timestamp range."""
    duration = duration_seconds(timestamps)
    if len(timestamps) < 2 or duration == 0.0:
        return 0.0
    return (len(timestamps) - 1) / duration


def magnitude(x: float, y: float, z: float) -> float:
    """Return the Euclidean magnitude of a three-axis sample."""
    return math.sqrt(x * x + y * y + z * z)


def mean(values: Sequence[float]) -> float:
    """Return the arithmetic mean, using zero for an empty series."""
    return statistics.fmean(values) if values else 0.0


def maximum(values: Sequence[float]) -> float:
    """Return the maximum, using zero for an empty series."""
    return max(values, default=0.0)


def minimum(values: Sequence[float]) -> float:
    """Return the minimum, using zero for an empty series."""
    return min(values, default=0.0)


def population_std(values: Sequence[float]) -> float:
    """Return population standard deviation, using zero when unavailable."""
    return statistics.pstdev(values) if len(values) > 1 else 0.0


def population_variance(values: Sequence[float]) -> float:
    """Return population variance, using zero when unavailable."""
    return statistics.pvariance(values) if len(values) > 1 else 0.0


def coefficient_of_variation(values: Sequence[float]) -> float:
    """Return std/mean, using zero for empty or zero-mean series."""
    average = mean(values)
    if average == 0.0:
        return 0.0
    return population_std(values) / abs(average)
