"""Tests for conftest."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("SUBSTRAKT_DEV", "1")
os.environ.setdefault("SUBSTRAKT_MODE", "airgap")

# Keep test data out of the user's application-data directory.
if "SUBSTRAKT_DATA_DIR" not in os.environ:
    _data = Path(tempfile.mkdtemp(prefix="substrakt-test-"))
    os.environ["SUBSTRAKT_DATA_DIR"] = str(_data)
    os.environ.setdefault("SUBSTRAKT_LOG_DIR", str(_data / "logs"))


# --- Shared fixtures -------------------------------------------------------


import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "corpus" / "out"


@pytest.fixture(scope="session", autouse=True)
def corpus() -> Path:
    """Generate the corpus if it is missing."""
    if not (CORPUS / "rechnung_din5008.pdf").exists():
        subprocess.run(
            [sys.executable, str(ROOT / "corpus" / "generate.py")],
            check=True,
            capture_output=True,
        )
    return CORPUS


@pytest.fixture
def store():
    from substrakt.config import load
    from substrakt.store import DocumentStore

    return DocumentStore(load())
