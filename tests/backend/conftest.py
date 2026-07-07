"""Fixtures for isolated backend API tests."""

import atexit
from collections.abc import Generator
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
from typing import Any


_test_runtime_dir = Path(tempfile.mkdtemp(prefix="experiment-platform-tests-"))
atexit.register(shutil.rmtree, _test_runtime_dir, ignore_errors=True)
os.environ.update(
    DATABASE_URL="sqlite:///:memory:",
    UPLOAD_DIR=str(_test_runtime_dir / "uploads"),
    TESTING_MODE="true",
    LOG_LEVEL="WARNING",
    PI_ADAPTER_MODE="noop",
    CORS_ORIGINS="http://testserver",
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.base import Base
from backend.app.dependencies import get_db
from backend.app.main import app
import backend.app.models  # noqa: F401


test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(
    bind=test_engine,
    class_=Session,
    autoflush=False,
    expire_on_commit=False,
)


@event.listens_for(test_engine, "connect")
def enable_test_foreign_keys(
    dbapi_connection: Any,
    connection_record: Any,
) -> None:
    """Enable SQLite cascades in the isolated test database."""

    del connection_record
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def override_database() -> Generator[Session, None, None]:
    """Provide a transaction-capable test database session."""

    database = TestSessionLocal()
    try:
        yield database
    finally:
        database.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Provide a clean API client and database for each test."""

    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_database
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def database_session(client: TestClient) -> Generator[Session, None, None]:
    """Provide direct database access for internal persistence assertions."""

    del client
    database = TestSessionLocal()
    try:
        yield database
    finally:
        database.close()
