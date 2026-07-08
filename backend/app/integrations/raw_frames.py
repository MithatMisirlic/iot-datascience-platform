"""File-backed storage boundary for exercise raw sensor frames."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Protocol

from shared.errors import InvalidArtifactError, MissingArtifactsError


Frame = dict[str, Any]


@dataclass(frozen=True, slots=True)
class RawExerciseFrames:
    """Raw numeric streams accepted by the generic processing pipeline."""

    imu: tuple[Frame, ...] = ()
    audio: tuple[Frame, ...] = ()
    mouth: tuple[Frame, ...] = ()

    @classmethod
    def from_sequences(
        cls,
        imu: Sequence[Mapping[str, Any]] = (),
        audio: Sequence[Mapping[str, Any]] = (),
        mouth: Sequence[Mapping[str, Any]] = (),
    ) -> "RawExerciseFrames":
        """Copy frame mappings into an immutable storage payload."""
        return cls(
            imu=tuple(dict(frame) for frame in imu),
            audio=tuple(dict(frame) for frame in audio),
            mouth=tuple(dict(frame) for frame in mouth),
        )

    def to_dict(self) -> dict[str, list[Frame]]:
        """Return a JSON-serializable representation."""
        return {
            "imu": [dict(frame) for frame in self.imu],
            "audio": [dict(frame) for frame in self.audio],
            "mouth": [dict(frame) for frame in self.mouth],
        }


class RawFrameStorage(Protocol):
    """Persist and load raw sensor frames for one exercise."""

    def save(self, exercise_id: str, frames: RawExerciseFrames) -> Path:
        """Persist all current raw streams for an exercise."""

    def load(self, exercise_id: str) -> RawExerciseFrames:
        """Load all raw streams for an exercise."""


class LocalJsonRawFrameStorage:
    """Store raw numeric frames as one JSON document per exercise."""

    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()
        filesystem_root = Path(self.root.anchor).resolve()
        if self.root == filesystem_root:
            raise ValueError("Raw-frame storage root must not be a filesystem root.")
        if self.root.exists() and not self.root.is_dir():
            raise ValueError("Raw-frame storage root must reference a directory.")

    def save(self, exercise_id: str, frames: RawExerciseFrames) -> Path:
        """Atomically write raw numeric streams below the configured root."""
        destination = self._path(exercise_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".json.tmp")
        try:
            temporary.write_text(
                json.dumps(frames.to_dict(), separators=(",", ":"), allow_nan=False),
                encoding="utf-8",
            )
            temporary.replace(destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return destination

    def load(self, exercise_id: str) -> RawExerciseFrames:
        """Load and minimally validate one exercise's raw-frame document."""
        source = self._path(exercise_id)
        if not source.is_file():
            raise MissingArtifactsError(
                f"Raw frames are not available for exercise {exercise_id}."
            )
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise TypeError("root must be an object")
            streams: dict[str, list[Mapping[str, Any]]] = {}
            for name in ("imu", "audio", "mouth"):
                stream = payload.get(name)
                if not isinstance(stream, list) or not all(
                    isinstance(frame, dict) for frame in stream
                ):
                    raise TypeError(f"{name} must be a list of objects")
                streams[name] = stream
        except (json.JSONDecodeError, OSError, TypeError) as error:
            raise InvalidArtifactError(
                f"Raw-frame data for exercise {exercise_id} is invalid: {error}"
            ) from error
        return RawExerciseFrames.from_sequences(**streams)

    def _path(self, exercise_id: str) -> Path:
        if not exercise_id or exercise_id in {".", ".."}:
            raise InvalidArtifactError("Exercise id is missing or invalid.")
        directory = (self.root / exercise_id).resolve()
        if not directory.is_relative_to(self.root) or directory == self.root:
            raise InvalidArtifactError("Exercise id produces an invalid storage path.")
        return directory / "raw_frames.json"

