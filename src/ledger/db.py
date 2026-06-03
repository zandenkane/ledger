"""SQLite setup, schema creation, and connection helper."""

import sqlite3
from pathlib import Path
from typing import Optional

from ledger.roles import seed_roles

_SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    medium TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    title TEXT NOT NULL,
    location TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS contributions (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    contributor TEXT NOT NULL,
    role TEXT NOT NULL,
    description TEXT,
    split_pct REAL,
    timestamp TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS roles (
    name TEXT PRIMARY KEY
);


def default_db_path() -> Path:
    """Return the default database path at ~/.ledger/ledger.db."""
    return Path.home() / ".ledger" / "ledger.db"


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Open a connection to the SQLite database, creating it if needed.

    Sets WAL mode and busy_timeout on every connection.
    Creates the schema and seeds roles on first use.
    """
    path = Path(db_path) if db_path else default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row

    conn.executescript(_SCHEMA)
    seed_roles(conn)

    return conn
