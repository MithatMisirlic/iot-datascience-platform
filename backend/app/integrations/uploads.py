"""Sensor-file ingestion boundary for a future upload implementation."""

from pathlib import Path
import shutil
from typing import BinaryIO, Protocol
from uuid import uuid4

from shared.enums import SensorFileType
from shared.errors import InvalidArtifactError, OperationDeferredError


class UploadReceiver(Protocol):
    """Store an uploaded sensor stream and return its storage path."""

    def receive(
        self,
        exercise_id: str,
        file_type: SensorFileType,
        filename: str,
        content: BinaryIO,
    ) -> str:
        """Receive one sensor file without depending on a web framework."""


class ArtifactStorage(UploadReceiver, Protocol):
    """Store and remove recording artifacts."""

    def delete(self, storage_path: str) -> None:
        """Delete one previously stored artifact if it exists."""


class LocalArtifactStorage:
    """Store artifact streams below a configured local directory."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        filesystem_root = Path(self.root.anchor).resolve()
        if self.root == filesystem_root:
            raise ValueError("Artifact storage root must not be a filesystem root.")
        if self.root.exists() and not self.root.is_dir():
            raise ValueError("Artifact storage root must reference a directory.")

    def receive(
        self,
        exercise_id: str,
        file_type: SensorFileType,
        filename: str,
        content: BinaryIO,
    ) -> str:
        """Write a stream to an exercise-specific directory."""

        safe_filename = Path(filename).name
        if not safe_filename or safe_filename in {".", ".."}:
            raise InvalidArtifactError("Artifact filename is missing or invalid.")

        directory = (self.root / exercise_id).resolve()
        if not directory.is_relative_to(self.root):
            raise InvalidArtifactError("Exercise id produces an invalid storage path.")
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / f"{uuid4()}_{file_type.value}_{safe_filename}"
        try:
            with destination.open("xb") as output:
                shutil.copyfileobj(content, output)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        return destination.relative_to(self.root).as_posix()

    def delete(self, storage_path: str) -> None:
        """Delete a path only when it remains inside the storage root."""

        target = (self.root / storage_path).resolve()
        if not target.is_relative_to(self.root):
            raise InvalidArtifactError("Artifact path escapes the storage root.")
        if not target.exists():
            return
        target.unlink()
        try:
            target.parent.rmdir()
        except OSError:
            pass


class DeferredUploadReceiver:
    """Reject uploads until transport and storage requirements are approved."""

    def receive(
        self,
        exercise_id: str,
        file_type: SensorFileType,
        filename: str,
        content: BinaryIO,
    ) -> str:
        """Raise a meaningful error instead of discarding uploaded content."""

        del exercise_id, file_type, filename, content
        raise OperationDeferredError(
            "Sensor uploads are deferred until the Pi upload flow is available."
        )

    def delete(self, storage_path: str) -> None:
        """Perform no cleanup because deferred uploads never store a file."""

        del storage_path
