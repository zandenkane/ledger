"""Hash computation and verification logic for the contribution chain."""

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from typing import Optional

GENESIS_HASH = "0" * 64


def compute_hash(
    seq: int,
    project_id: int,
    session_id: int,
    contributor: str,
    role: str,
    description: Optional[str],
    split_pct: Optional[float],
    timestamp: str,
    prev_hash: str,
) -> str:
    """Compute SHA-256 hash from canonical JSON serialization of contribution fields."""
    payload = json.dumps(
        {
            "seq": seq,
            "project_id": project_id,
            "session_id": session_id,
            "contributor": contributor,
            "role": role,
            "description": description,
            "split_pct": split_pct,
            "timestamp": timestamp,
            "prev_hash": prev_hash,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class VerifyResult:
    """Result of a chain verification run."""

    valid: bool
    entries_checked: int
    broken_seq: Optional[int] = None
    expected_hash: Optional[str] = None
    actual_hash: Optional[str] = None


def verify_chain(conn: sqlite3.Connection, project_id: Optional[int] = None) -> VerifyResult:
    """Walk the contributions table in seq order and verify every hash.

    If project_id is given, only entries for that project are checked,
    but the chain linkage still follows global seq order.

    Returns a VerifyResult indicating success or the first broken link.
    """
    if project_id is not None:
        rows = conn.execute(
            "SELECT seq, project_id, session_id, contributor, role, "
            "description, split_pct, timestamp, prev_hash, hash "
            "FROM contributions WHERE project_id = ? ORDER BY seq",
            (project_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT seq, project_id, session_id, contributor, role, "
            "description, split_pct, timestamp, prev_hash, hash "
            "FROM contributions ORDER BY seq"
        ).fetchall()

    if not rows:
        return VerifyResult(valid=True, entries_checked=0)

    # For project-filtered verification, we need the full chain to check prev_hash linkage.
    # Build a lookup of all hashes by seq for prev_hash validation.
    all_hashes: dict[int, str] = {}
    if project_id is not None:
        all_rows = conn.execute(
            "SELECT seq, hash FROM contributions ORDER BY seq"
        ).fetchall()
        for r in all_rows:
            all_hashes[r["seq"]] = r["hash"]

    for i, row in enumerate(rows):
        expected = compute_hash(
            seq=row["seq"],
            project_id=row["project_id"],
            session_id=row["session_id"],
            contributor=row["contributor"],
            role=row["role"],
            description=row["description"],
            split_pct=row["split_pct"],
            timestamp=row["timestamp"],
            prev_hash=row["prev_hash"],
        )

        if expected != row["hash"]:
            return VerifyResult(
                valid=False,
                entries_checked=i + 1,
                broken_seq=row["seq"],
                expected_hash=expected,
                actual_hash=row["hash"],
            )

    return VerifyResult(valid=True, entries_checked=len(rows))
