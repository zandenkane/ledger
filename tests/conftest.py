"""Shared pytest fixtures for ledger tests."""

import sys
from pathlib import Path

# Ensure src/ is first on sys.path so our package takes priority
# over any same-named directory at the repo root.
_src = str(Path(__file__).resolve().parent.parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

# Remove repo root from sys.path if present, to avoid shadowing.
_root = str(Path(__file__).resolve().parent.parent)
if _root in sys.path:
    sys.path.remove(_root)

import pytest  # noqa: E402

import ledger.cli as cli_mod  # noqa: E402
from ledger.db import get_connection  # noqa: E402


@pytest.fixture()
def db_conn(tmp_path):
    """Yield a fresh SQLite connection backed by a temp file."""
    db_file = tmp_path / "test.db"
    conn = get_connection(str(db_file))
    yield conn
    conn.close()


@pytest.fixture()
def cli_db(tmp_path):
    """Set the CLI module to use a temp database and return the path."""
    db_file = tmp_path / "cli_test.db"
    cli_mod._db_path_override = str(db_file)
    yield str(db_file)
    cli_mod._db_path_override = None
