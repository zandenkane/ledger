"""Tests for database schema creation and basic CRUD operations."""

from ledger.db import get_connection
from ledger.roles import KNOWN_ROLES


def test_schema_creates_tables(db_conn):
    """All four tables exist after connection setup."""
    tables = db_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    table_names = sorted(row["name"] for row in tables)
    assert "contributions" in table_names
    assert "projects" in table_names
    assert "roles" in table_names
    assert "sessions" in table_names


def test_roles_seeded(db_conn):
    """Known roles are present after connection setup."""
    rows = db_conn.execute("SELECT name FROM roles ORDER BY name").fetchall()
    role_names = [row["name"] for row in rows]
    for role in KNOWN_ROLES:
        assert role in role_names


def test_wal_mode(db_conn):
    """WAL journal mode is enabled."""
    mode = db_conn.execute("PRAGMA journal_mode").fetchone()
    assert mode[0] == "wal"


def test_foreign_keys_enabled(db_conn):
    """Foreign keys are enforced."""
    fk = db_conn.execute("PRAGMA foreign_keys").fetchone()
    assert fk[0] == 1


def test_insert_project(db_conn):
    """Can insert and retrieve a project."""
    db_conn.execute(
        "INSERT INTO projects (name, medium, created_at) VALUES (?, ?, ?)",
        ("MyAlbum", "music", "2026-01-01T00:00:00+00:00"),
    )
    db_conn.commit()

    row = db_conn.execute("SELECT * FROM projects WHERE name = 'MyAlbum'").fetchone()
    assert row["name"] == "MyAlbum"
    assert row["medium"] == "music"


def test_unique_project_name(db_conn):
    """Duplicate project names are rejected."""
    db_conn.execute(
        "INSERT INTO projects (name, medium, created_at) VALUES (?, ?, ?)",
        ("Dup", "music", "2026-01-01T00:00:00+00:00"),
    )
    db_conn.commit()

    import sqlite3

    import pytest

    with pytest.raises(sqlite3.IntegrityError):
        db_conn.execute(
            "INSERT INTO projects (name, medium, created_at) VALUES (?, ?, ?)",
            ("Dup", "film", "2026-01-02T00:00:00+00:00"),
        )


def test_insert_session(db_conn):
    """Can insert a session tied to a project."""
    db_conn.execute(
        "INSERT INTO projects (name, medium, created_at) VALUES (?, ?, ?)",
        ("Proj", "music", "2026-01-01T00:00:00+00:00"),
    )
    db_conn.execute(
        "INSERT INTO sessions (project_id, title, started_at) VALUES (?, ?, ?)",
        (1, "Day 1", "2026-01-01T09:00:00+00:00"),
    )
    db_conn.commit()

    row = db_conn.execute("SELECT * FROM sessions WHERE title = 'Day 1'").fetchone()
    assert row["project_id"] == 1
    assert row["ended_at"] is None


def test_connection_creates_directory(tmp_path):
    """get_connection creates the parent directory if it doesn't exist."""
    db_file = tmp_path / "subdir" / "nested" / "test.db"
    conn = get_connection(str(db_file))
    assert db_file.exists()
    conn.close()


def test_idempotent_schema(tmp_path):
    """Calling get_connection twice on the same file doesn't error."""
    db_file = tmp_path / "idem.db"
    conn1 = get_connection(str(db_file))
    conn1.close()
    conn2 = get_connection(str(db_file))
    tables = conn2.execute(
        "SELECT COUNT(*) as c FROM sqlite_master WHERE type='table'"
    ).fetchone()
    assert tables["c"] >= 4
    conn2.close()
