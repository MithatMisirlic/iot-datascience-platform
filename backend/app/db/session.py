"""SQLAlchemy engine and session factory configuration."""

import os
import sqlite3
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./experiment_platform.db")


def _engine_options(database_url: str) -> dict[str, Any]:
    """Return driver-specific engine options."""

    if database_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {}


engine = create_engine(DATABASE_URL, **_engine_options(DATABASE_URL))

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    expire_on_commit=False,
)


@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(
    dbapi_connection: Any,
    connection_record: Any,
) -> None:
    """Enable foreign-key enforcement for every SQLite connection."""

    del connection_record
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
