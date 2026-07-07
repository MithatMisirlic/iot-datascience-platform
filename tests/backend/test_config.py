"""Tests for centralized backend settings and runtime validation."""

from pathlib import Path

from pydantic import ValidationError
import pytest
from sqlalchemy import create_engine

from backend.app.core.config import Settings
from backend.app.db import init_db


def test_settings_parse_and_normalize_values(tmp_path: Path) -> None:
    """Parse typed settings and comma-separated browser origins."""

    settings = Settings(
        _env_file=None,
        database_url="sqlite:///:memory:",
        upload_dir=tmp_path / "uploads",
        testing_mode=True,
        log_level="debug",
        pi_adapter_mode="noop",
        cors_origins="http://localhost:3000, http://localhost:8501",
    )

    assert settings.testing_mode is True
    assert settings.log_level == "DEBUG"
    assert settings.resolved_upload_dir == (tmp_path / "uploads").resolve()
    assert settings.cors_origin_list == [
        "http://localhost:3000",
        "http://localhost:8501",
    ]
    settings.validate_runtime()


def test_settings_load_dotenv_with_environment_precedence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load a dotenv file while allowing process variables to override it."""

    env_file = tmp_path / ".env"
    upload_dir = tmp_path / "dotenv-uploads"
    env_file.write_text(
        "\n".join(
            [
                "DATABASE_URL=sqlite:///:memory:",
                f"UPLOAD_DIR={upload_dir.as_posix()}",
                "TESTING_MODE=true",
                "LOG_LEVEL=debug",
                "PI_ADAPTER_MODE=noop",
                "CORS_ORIGINS=http://dotenv.example",
            ]
        ),
        encoding="utf-8",
    )
    for variable in (
        "DATABASE_URL",
        "UPLOAD_DIR",
        "TESTING_MODE",
        "LOG_LEVEL",
        "PI_ADAPTER_MODE",
        "CORS_ORIGINS",
    ):
        monkeypatch.delenv(variable, raising=False)

    dotenv_settings = Settings(_env_file=env_file)
    assert dotenv_settings.testing_mode is True
    assert dotenv_settings.log_level == "DEBUG"
    assert dotenv_settings.resolved_upload_dir == upload_dir.resolve()

    monkeypatch.setenv("LOG_LEVEL", "ERROR")
    overridden_settings = Settings(_env_file=env_file)
    assert overridden_settings.log_level == "ERROR"


def test_settings_reject_empty_database_url_and_unsupported_pi_mode(
    tmp_path: Path,
) -> None:
    """Reject unusable database and unimplemented hardware configuration."""

    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(_env_file=None, database_url="", upload_dir=tmp_path / "uploads")

    with pytest.raises(ValidationError, match="pi_adapter_mode"):
        Settings(
            _env_file=None,
            database_url="sqlite:///:memory:",
            upload_dir=tmp_path / "uploads",
            pi_adapter_mode="raspberry_pi",  # type: ignore[arg-type]
        )


def test_runtime_validation_rejects_unsafe_upload_paths(tmp_path: Path) -> None:
    """Reject filesystem roots and existing files as upload directories."""

    filesystem_root = Path(tmp_path.anchor)
    root_settings = Settings(
        _env_file=None,
        database_url="sqlite:///:memory:",
        upload_dir=filesystem_root,
    )
    with pytest.raises(ValueError, match="filesystem root"):
        root_settings.validate_runtime()

    file_path = tmp_path / "not-a-directory"
    file_path.write_text("content", encoding="ascii")
    file_settings = Settings(
        _env_file=None,
        database_url="sqlite:///:memory:",
        upload_dir=file_path,
    )
    with pytest.raises(ValueError, match="directory"):
        file_settings.validate_runtime()


def test_sqlite_path_preparation_creates_parent_and_rejects_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prepare nested SQLite paths and reject a directory as the database file."""

    database_path = tmp_path / "nested" / "database.sqlite3"
    file_engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    monkeypatch.setattr(init_db, "engine", file_engine)
    init_db.prepare_database_path()
    assert database_path.parent.is_dir()
    file_engine.dispose()

    directory_path = tmp_path / "database-directory"
    directory_path.mkdir()
    directory_engine = create_engine(f"sqlite:///{directory_path.as_posix()}")
    monkeypatch.setattr(init_db, "engine", directory_engine)
    with pytest.raises(ValueError, match="file, not a directory"):
        init_db.prepare_database_path()
    directory_engine.dispose()
