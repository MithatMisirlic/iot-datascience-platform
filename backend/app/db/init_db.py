"""Database schema initialization helpers."""

from backend.app.db.base import Base
from backend.app.db.session import engine


def create_tables() -> None:
    """Create all model tables that do not already exist."""

    # Importing the model package registers every mapping on Base.metadata.
    import backend.app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
