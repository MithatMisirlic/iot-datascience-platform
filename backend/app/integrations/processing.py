"""Processed-result generation boundary for a future data pipeline."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from shared.enums import SensorFileType
from shared.errors import OperationDeferredError


@dataclass(frozen=True, slots=True)
class ProcessingArtifact:
    """Dependency-free metadata describing one stored processing input."""

    file_type: SensorFileType
    original_filename: str
    storage_path: str


class ResultProcessor(Protocol):
    """Generate contract-shaped feature data for an exercise."""

    required_file_types: frozenset[SensorFileType]

    def process(
        self,
        exercise_id: str,
        artifacts: Sequence[ProcessingArtifact],
    ) -> dict[str, Any]:
        """Return processed feature JSON for an exercise."""


class DeferredResultProcessor:
    """Reject processing until the real pipeline is connected."""

    required_file_types = frozenset(SensorFileType)

    def process(
        self,
        exercise_id: str,
        artifacts: Sequence[ProcessingArtifact],
    ) -> dict[str, Any]:
        """Raise a meaningful error instead of simulating processing."""

        del exercise_id, artifacts
        raise OperationDeferredError(
            "Result processing is deferred until the data pipeline is available."
        )
