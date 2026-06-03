"""Tests for JSON and CSV export."""

import csv
import io
import json

from ledger.chain import GENESIS_HASH, compute_hash
from ledger.export import export_csv, export_json


def _setup_data(conn):
    """Insert a project, session, and two contributions."""
    conn.execute(
        "INSERT INTO projects (name, medium, created_at) VALUES (?, ?, ?)",
        ("ExportProj", "music", "2026-01-01T00:00:00+00:00"),
    )
    conn.execute(
        "INSERT INTO sessions (project_id, title, started_at) VALUES (?, ?, ?)",
        (1, "Session 1", "2026-01-01T09:00:00+00:00"),
    )
    conn.commit()

    ts1 = "2026-01-01T10:00:00+00:00"
    h1 = compute_hash(1, 1, 1, "Alice", "producer", "Produced", 60.0, ts1, GENESIS_HASH)
    conn.execute(
        "INSERT INTO contributions "
        "(project_id, session_id, contributor, role, description, split_pct, "
        "timestamp, prev_hash, hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (1, 1, "Alice", "producer", "Produced", 60.0, ts1, GENESIS_HASH, h1),
    )

    ts2 = "2026-01-01T11:00:00+00:00"
    h2 = compute_hash(2, 1, 1, "Bob", "engineer", "Mixed", 40.0, ts2, h1)
    conn.execute(
        "INSERT INTO contributions "
        "(project_id, session_id, contributor, role, description, split_pct, "
        "timestamp, prev_hash, hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (1, 1, "Bob", "engineer", "Mixed", 40.0, ts2, h1, h2),
    )
    conn.commit()
    return h1, h2


def test_export_json_structure(db_conn):
    """JSON export contains all expected fields."""
    _setup_data(db_conn)
    output = export_json(db_conn, 1)
    data = json.loads(output)

    assert len(data) == 2
    entry = data[0]
    assert entry["contributor"] == "Alice"
    assert entry["role"] == "producer"
    assert entry["split_pct"] == 60.0
    assert "hash" in entry
    assert "prev_hash" in entry
    assert "seq" in entry


def test_export_json_order(db_conn):
    """JSON export is ordered by seq."""
    _setup_data(db_conn)
    data = json.loads(export_json(db_conn, 1))
    assert data[0]["seq"] < data[1]["seq"]


def test_export_json_empty_project(db_conn):
    """JSON export of a project with no contributions returns empty list."""
    db_conn.execute(
        "INSERT INTO projects (name, medium, created_at) VALUES (?, ?, ?)",
        ("Empty", "art", "2026-01-01T00:00:00+00:00"),
    )
    db_conn.commit()
    output = export_json(db_conn, 1)
    assert json.loads(output) == []


def test_export_csv_structure(db_conn):
    """CSV export contains headers and data rows."""
    _setup_data(db_conn)
    output = export_csv(db_conn, 1)
    reader = csv.DictReader(io.StringIO(output))
    rows = list(reader)

    assert len(rows) == 2
    assert rows[0]["contributor"] == "Alice"
    assert rows[1]["contributor"] == "Bob"
    assert "hash" in rows[0]
    assert "prev_hash" in rows[0]


def test_export_csv_headers(db_conn):
    """CSV export has the correct column headers."""
    _setup_data(db_conn)
    output = export_csv(db_conn, 1)
    first_line = output.split("\n")[0]
    expected_headers = [
        "seq", "project_id", "session_id", "contributor", "role",
        "description", "split_pct", "timestamp", "prev_hash", "hash",
    ]
    for header in expected_headers:
        assert header in first_line


def test_export_csv_empty(db_conn):
    """CSV export of empty project has only headers."""
    db_conn.execute(
        "INSERT INTO projects (name, medium, created_at) VALUES (?, ?, ?)",
        ("Empty", "art", "2026-01-01T00:00:00+00:00"),
    )
    db_conn.commit()
    output = export_csv(db_conn, 1)
    lines = [line for line in output.strip().split("\n") if line]
    assert len(lines) == 1  # Just the header row.


def test_export_json_null_split(db_conn):
    """JSON export handles null split_pct correctly."""
    db_conn.execute(
        "INSERT INTO projects (name, medium, created_at) VALUES (?, ?, ?)",
        ("NullSplit", "music", "2026-01-01T00:00:00+00:00"),
    )
    db_conn.execute(
        "INSERT INTO sessions (project_id, title, started_at) VALUES (?, ?, ?)",
        (1, "S1", "2026-01-01T00:00:00+00:00"),
    )
    ts = "2026-01-01T10:00:00+00:00"
    h = compute_hash(1, 1, 1, "Alice", "producer", "Stuff", None, ts, GENESIS_HASH)
    db_conn.execute(
        "INSERT INTO contributions "
        "(project_id, session_id, contributor, role, description, split_pct, "
        "timestamp, prev_hash, hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (1, 1, "Alice", "producer", "Stuff", None, ts, GENESIS_HASH, h),
    )
    db_conn.commit()

    data = json.loads(export_json(db_conn, 1))
    assert data[0]["split_pct"] is None
