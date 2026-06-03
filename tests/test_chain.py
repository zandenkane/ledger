"""Tests for hash computation and chain verification."""

from datetime import datetime, timezone

from ledger.chain import GENESIS_HASH, compute_hash, verify_chain


def test_compute_hash_deterministic():
    """Same inputs always produce the same hash."""
    kwargs = dict(
        seq=1,
        project_id=1,
        session_id=1,
        contributor="Alice",
        role="producer",
        description="Produced the track",
        split_pct=50.0,
        timestamp="2026-01-01T00:00:00+00:00",
        prev_hash=GENESIS_HASH,
    )
    h1 = compute_hash(**kwargs)
    h2 = compute_hash(**kwargs)
    assert h1 == h2
    assert len(h1) == 64


def test_compute_hash_different_inputs():
    """Different inputs produce different hashes."""
    base = dict(
        seq=1,
        project_id=1,
        session_id=1,
        contributor="Alice",
        role="producer",
        description="Produced the track",
        split_pct=50.0,
        timestamp="2026-01-01T00:00:00+00:00",
        prev_hash=GENESIS_HASH,
    )
    h1 = compute_hash(**base)
    h2 = compute_hash(**{**base, "contributor": "Bob"})
    assert h1 != h2


def test_compute_hash_none_split():
    """Null split_pct is handled correctly."""
    h = compute_hash(
        seq=1,
        project_id=1,
        session_id=1,
        contributor="Alice",
        role="producer",
        description=None,
        split_pct=None,
        timestamp="2026-01-01T00:00:00+00:00",
        prev_hash=GENESIS_HASH,
    )
    assert len(h) == 64


def _insert_contribution(conn, seq, project_id, session_id, contributor, role,
                          description, split_pct, prev_hash):
    """Helper to insert a contribution with correct hash."""
    ts = datetime.now(timezone.utc).isoformat()
    entry_hash = compute_hash(
        seq=seq,
        project_id=project_id,
        session_id=session_id,
        contributor=contributor,
        role=role,
        description=description,
        split_pct=split_pct,
        timestamp=ts,
        prev_hash=prev_hash,
    )
    conn.execute(
        "INSERT INTO contributions "
        "(project_id, session_id, contributor, role, description, split_pct, "
        "timestamp, prev_hash, hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (project_id, session_id, contributor, role, description, split_pct,
         ts, prev_hash, entry_hash),
    )
    conn.commit()
    return entry_hash


def _setup_project_and_session(conn):
    """Create a project and session, return (project_id, session_id)."""
    conn.execute(
        "INSERT INTO projects (name, medium, created_at) VALUES (?, ?, ?)",
        ("TestProject", "music", "2026-01-01T00:00:00+00:00"),
    )
    conn.execute(
        "INSERT INTO sessions (project_id, title, started_at) VALUES (?, ?, ?)",
        (1, "Session 1", "2026-01-01T00:00:00+00:00"),
    )
    conn.commit()
    return 1, 1


def test_verify_empty_chain(db_conn):
    """Empty chain is valid."""
    result = verify_chain(db_conn)
    assert result.valid is True
    assert result.entries_checked == 0


def test_verify_single_entry(db_conn):
    """Single valid entry passes verification."""
    pid, sid = _setup_project_and_session(db_conn)
    _insert_contribution(db_conn, 1, pid, sid, "Alice", "producer", "Did stuff", 50.0, GENESIS_HASH)

    result = verify_chain(db_conn)
    assert result.valid is True
    assert result.entries_checked == 1


def test_verify_chain_of_three(db_conn):
    """Three linked entries pass verification."""
    pid, sid = _setup_project_and_session(db_conn)

    h1 = _insert_contribution(
        db_conn, 1, pid, sid, "Alice", "producer", "Produced", 50.0, GENESIS_HASH,
    )
    h2 = _insert_contribution(db_conn, 2, pid, sid, "Bob", "engineer", "Mixed", 30.0, h1)
    _insert_contribution(db_conn, 3, pid, sid, "Carol", "performer", "Sang", 20.0, h2)

    result = verify_chain(db_conn)
    assert result.valid is True
    assert result.entries_checked == 3


def test_verify_detects_tamper(db_conn):
    """Modifying a stored hash breaks verification."""
    pid, sid = _setup_project_and_session(db_conn)

    h1 = _insert_contribution(
        db_conn, 1, pid, sid, "Alice", "producer", "Produced", 50.0, GENESIS_HASH,
    )
    _insert_contribution(db_conn, 2, pid, sid, "Bob", "engineer", "Mixed", 30.0, h1)

    # Tamper with the first entry's hash.
    db_conn.execute("UPDATE contributions SET hash = 'tampered' WHERE seq = 1")
    db_conn.commit()

    result = verify_chain(db_conn)
    assert result.valid is False
    assert result.broken_seq == 1


def test_verify_detects_field_tamper(db_conn):
    """Modifying a stored field (not the hash) breaks verification."""
    pid, sid = _setup_project_and_session(db_conn)
    _insert_contribution(db_conn, 1, pid, sid, "Alice", "producer", "Produced", 50.0, GENESIS_HASH)

    # Tamper with the contributor field.
    db_conn.execute("UPDATE contributions SET contributor = 'Eve' WHERE seq = 1")
    db_conn.commit()

    result = verify_chain(db_conn)
    assert result.valid is False
    assert result.broken_seq == 1


def test_verify_project_filter(db_conn):
    """Verification can filter by project."""
    # Create two projects.
    db_conn.execute(
        "INSERT INTO projects (name, medium, created_at) VALUES (?, ?, ?)",
        ("ProjA", "music", "2026-01-01T00:00:00+00:00"),
    )
    db_conn.execute(
        "INSERT INTO projects (name, medium, created_at) VALUES (?, ?, ?)",
        ("ProjB", "film", "2026-01-01T00:00:00+00:00"),
    )
    db_conn.execute(
        "INSERT INTO sessions (project_id, title, started_at) VALUES (?, ?, ?)",
        (1, "S1", "2026-01-01T00:00:00+00:00"),
    )
    db_conn.execute(
        "INSERT INTO sessions (project_id, title, started_at) VALUES (?, ?, ?)",
        (2, "S2", "2026-01-01T00:00:00+00:00"),
    )
    db_conn.commit()

    h1 = _insert_contribution(db_conn, 1, 1, 1, "Alice", "producer", "Produced", None, GENESIS_HASH)
    _insert_contribution(db_conn, 2, 2, 2, "Bob", "director", "Directed", None, h1)

    # Verify just project 1.
    result = verify_chain(db_conn, project_id=1)
    assert result.valid is True
    assert result.entries_checked == 1
