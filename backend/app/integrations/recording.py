"""Recording command boundary for a future Raspberry Pi adapter.

Individual motion, audio, and camera capture remain Pi-side implementation
details until the device transport and recording protocol can be tested.
"""

from typing import Protocol


class RecordingBackend(Protocol):
    """Issue recording commands without exposing device implementation details."""

    def start_recording(self, exercise_id: str) -> None:
        """Start external capture for an exercise."""

    def stop_recording(self, exercise_id: str) -> None:
        """Stop external capture for an exercise."""


class NoOpRecordingBackend:
    """Allow database-only lifecycle operation while hardware is unavailable."""

    def start_recording(self, exercise_id: str) -> None:
        """Intentionally perform no external operation."""

        del exercise_id

    def stop_recording(self, exercise_id: str) -> None:
        """Intentionally perform no external operation."""

        del exercise_id
