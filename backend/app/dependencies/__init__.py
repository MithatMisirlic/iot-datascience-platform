"""FastAPI dependency providers."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Provide one SQLAlchemy session for the lifetime of a request."""

    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()


DatabaseSession = Annotated[Session, Depends(get_db)]
