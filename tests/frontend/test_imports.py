"""Import-path tests for Streamlit frontend modules."""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_frontend_is_package() -> None:
    """The frontend package marker must remain available."""

    module = importlib.import_module("frontend")

    assert module.__file__ is not None


def test_streamlit_page_modules_import_as_package_modules() -> None:
    """Native Streamlit page modules should import without path errors."""

    for module_name in (
        "frontend.app",
        "frontend.pages.experiments",
        "frontend.pages.live_experiment",
        "frontend.pages.recording",
        "frontend.pages.results",
    ):
        importlib.import_module(module_name)


def test_requested_python_import_commands_work() -> None:
    """Validate the exact import shape documented for this fix."""

    for module_name in (
        "frontend.app",
        "frontend.pages.experiments",
        "frontend.pages.live_experiment",
        "frontend.pages.recording",
        "frontend.pages.results",
    ):
        subprocess.run(
            [sys.executable, "-c", f"import {module_name}"],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
