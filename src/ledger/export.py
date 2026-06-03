"""JSON and CSV export of contributions and credits."""

import csv
import io
import json
import sqlite3


def export_json(conn: sqlite3.Connection, project_id: int) -> str:
    rows = conn.execute(
        "SELECT seq, project_id, session_id, contributor, role, "
        "description, split_pct, timestamp, prev_hash, hash "
        "FROM contributions WHERE project_id = ? ORDER BY seq",
        (project_id,),
    ).fetchall()

    entries = []
    for row in rows:
        entries.append(
            {
                "seq": row["seq"],
                "project_id": row["project_id"],
                "session_id": row["session_id"],
                "contributor": row["contributor"],
                "role": row["role"],
                "description": row["description"],
                "split_pct": row["split_pct"],
                "timestamp": row["timestamp"],
                "prev_hash": row["prev_hash"],
                "hash": row["hash"],
            }
        )

    return json.dumps(entries, indent=2)


def export_csv(conn: sqlite3.Connection, project_id: int) -> str:
    """Export all contributions for a project as a CSV string."""
    rows = conn.execute(
        "SELECT seq, project_id, session_id, contributor, role, "
        "description, split_pct, timestamp, prev_hash, hash "
        "FROM contributions WHERE project_id = ? ORDER BY seq",
        (project_id,),
    ).fetchall()

    output = io.StringIO()
    fieldnames = [
        "seq",
        "project_id",
        "session_id",
        "contributor",
        "role",
        "description",
        "split_pct",
        "timestamp",
        "prev_hash",
        "hash",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for row in rows:
        writer.writerow(
            {
                "seq": row["seq"],
                "project_id": row["project_id"],
                "session_id": row["session_id"],
                "contributor": row["contributor"],
                "role": row["role"],
                "description": row["description"],
                "split_pct": row["split_pct"],
                "timestamp": row["timestamp"],
                "prev_hash": row["prev_hash"],
                "hash": row["hash"],
            }
        )

    return output.getvalue()
