"""Database schema initialization helpers."""

from pathlib import Path

from backend.app.db.base import Base
from backend.app.db.session import engine


def prepare_database_path() -> None:
    """Create the parent directory for a file-backed SQLite database."""

    if engine.url.get_backend_name() != "sqlite":
        return
    database = engine.url.database
    if not database or database == ":memory:" or database.startswith("file:"):
        return
    database_path = Path(database).expanduser().resolve()
    if database_path.exists() and database_path.is_dir():
        raise ValueError("SQLite DATABASE_URL must reference a file, not a directory.")
    database_path.parent.mkdir(parents=True, exist_ok=True)


def create_tables() -> None:
    """Create all model tables that do not already exist."""

    prepare_database_path()
    # Importing the model package registers every mapping on Base.metadata.
    import backend.app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
