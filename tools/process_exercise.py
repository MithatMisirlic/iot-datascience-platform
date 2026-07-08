"""Development CLI for processing one exercise's stored raw frames."""

from __future__ import annotations

import argparse
import json
import sys

from backend.app.core.config import settings
from backend.app.db.init_db import create_tables
from backend.app.db.session import SessionLocal
from backend.app.integrations.raw_frames import (
    LocalJsonRawFrameStorage,
    RawExerciseFrames,
)
from backend.app.services import exercise_service, processing_service


def sample_raw_frames() -> RawExerciseFrames:
    """Return a small deterministic hardware-free processing sample."""
    return RawExerciseFrames.from_sequences(
        imu=[
            {
                "ts": 0.0,
                "accel_x": 16_384,
                "accel_y": 0,
                "accel_z": 0,
                "gyro_x": 131,
                "gyro_y": 0,
                "gyro_z": 0,
            },
            {
                "ts": 1.0,
                "accel_x": 0,
                "accel_y": 16_384,
                "accel_z": 0,
                "gyro_x": 0,
                "gyro_y": 131,
                "gyro_z": 0,
            },
        ],
        audio=[{"ts": 0.0, "spl": 0.2}, {"ts": 1.0, "spl": 0.4}],
        mouth=[
            {"ts": 0.0, "vertical": 0.2, "horizontal": 0.5},
            {"ts": 1.0, "vertical": 0.3, "horizontal": 0.6},
        ],
    )


def parse_args() -> argparse.Namespace:
    """Parse the exercise identifier and optional sample generation flag."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exercise_id", help="Existing exercise UUID")
    parser.add_argument(
        "--generate-sample",
        action="store_true",
        help="Write deterministic sample raw frames before processing",
    )
    return parser.parse_args()


def main() -> None:
    """Prepare local resources, process one exercise, and print JSON output."""
    args = parse_args()
    settings.validate_runtime()
    settings.resolved_raw_frame_dir.mkdir(parents=True, exist_ok=True)
    create_tables()
    storage = LocalJsonRawFrameStorage(settings.resolved_raw_frame_dir)

    try:
        with SessionLocal() as database:
            exercise_service.get_exercise(database, args.exercise_id)
            if args.generate_sample:
                storage.save(args.exercise_id, sample_raw_frames())
            result = processing_service.process_raw_exercise(
                database,
                args.exercise_id,
                storage,
            )
    except Exception as error:
        print(f"Processing failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

