"""Typer CLI application with all command definitions."""

from datetime import datetime, timezone
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ledger.chain import GENESIS_HASH, compute_hash, verify_chain
from ledger.db import get_connection
from ledger.export import export_csv, export_json
from ledger.models import Project, Session

app = typer.Typer(help="Tamper-evident contribution ledger for creative projects.")
project_app = typer.Typer(help="Manage projects.")
session_app = typer.Typer(help="Manage recording sessions.")
app.add_typer(project_app, name="project")
app.add_typer(session_app, name="session")

console = Console()

# Module-level override for the database path (used in tests).
_db_path_override: Optional[str] = None


def _conn():
    return get_connection(_db_path_override)


def _row_to_project(row) -> Project:
    return Project(
        id=row["id"],
        name=row["name"],
        medium=row["medium"],
        created_at=row["created_at"],
    )


def _row_to_session(row) -> Session:
    return Session(
        id=row["id"],
        project_id=row["project_id"],
        title=row["title"],
        location=row["location"],
        started_at=row["started_at"],
        ended_at=row["ended_at"],
        notes=row["notes"],
    )


def _lookup_project(conn, name: str):
    row = conn.execute("SELECT * FROM projects WHERE name = ?", (name,)).fetchone()
    if not row:
        console.print(f"[red]Project '{name}' not found.[/red]")
        conn.close()
        raise typer.Exit(code=1)
    return _row_to_project(row)


# Project commands


@project_app.command("create")
def project_create(
    name: str = typer.Argument(..., help="Project name (must be unique)."),
    medium: str = typer.Option(
        "other",
        help="Medium type: music, film, art, or other.",
    ),
):
    """Create a new project."""
    valid_mediums = ("music", "film", "art", "other")
    if medium not in valid_mediums:
        console.print(f"[red]Medium must be one of: {', '.join(valid_mediums)}[/red]")
        raise typer.Exit(code=1)

    conn = _conn()
    now = datetime.now(timezone.utc).isoformat()
    try:
        conn.execute(
            "INSERT INTO projects (name, medium, created_at) VALUES (?, ?, ?)",
            (name, medium, now),
        )
        conn.commit()
        console.print(f"[green]Project '{name}' created.[/green]")
    except Exception:
        console.print(f"[red]Project '{name}' already exists.[/red]")
        raise typer.Exit(code=1)
    finally:
        conn.close()


@project_app.command("list")
def project_list():
    """List all projects."""
    conn = _conn()
    rows = conn.execute("SELECT * FROM projects ORDER BY id").fetchall()
    conn.close()

    if not rows:
        console.print("No projects found.")
        return

    table = Table(title="Projects")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("Medium")
    table.add_column("Created")

    for row in rows:
        proj = _row_to_project(row)
        table.add_row(str(proj.id), proj.name, proj.medium, proj.created_at)

    console.print(table)


@project_app.command("delete")
def project_delete(
    name: str = typer.Argument(..., help="Project name to delete."),
    force: bool = typer.Option(False, help="Skip confirmation prompt."),
):
    """Delete a project and all its sessions and contributions."""
    conn = _conn()
    proj = _lookup_project(conn, name)

    contrib_count = conn.execute(
        "SELECT COUNT(*) as c FROM contributions WHERE project_id = ?",
        (proj.id,),
    ).fetchone()["c"]

    session_count = conn.execute(
        "SELECT COUNT(*) as c FROM sessions WHERE project_id = ?",
        (proj.id,),
    ).fetchone()["c"]

    if not force:
        console.print(
            f"[yellow]This will delete project '{name}' with "
            f"{session_count} session(s) and {contrib_count} contribution(s).[/yellow]"
        )
        confirm = typer.confirm("Proceed?")
        if not confirm:
            console.print("Aborted.")
            conn.close()
            return

    conn.execute("DELETE FROM contributions WHERE project_id = ?", (proj.id,))
    conn.execute("DELETE FROM sessions WHERE project_id = ?", (proj.id,))
    conn.execute("DELETE FROM projects WHERE id = ?", (proj.id,))
    conn.commit()
    conn.close()
    console.print(f"[green]Project '{name}' deleted.[/green]")


# Session commands


@session_app.command("start")
def session_start(
    project: str = typer.Argument(..., help="Project name."),
    title: str = typer.Argument(..., help="Session title."),
    location: Optional[str] = typer.Option(None, help="Session location."),
    notes: Optional[str] = typer.Option(None, help="Session notes."),
):
    conn = _conn()
    proj = _lookup_project(conn, project)

    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO sessions (project_id, title, location, started_at, notes) "
        "VALUES (?, ?, ?, ?, ?)",
        (proj.id, title, location, now, notes),
    )
    conn.commit()
    session_id = cursor.lastrowid
    console.print(f"[green]Session {session_id} started: '{title}'[/green]")
    conn.close()


@session_app.command("end")
def session_end(
    project: str = typer.Argument(..., help="Project name."),
    session_id: Optional[int] = typer.Argument(None, help="Session ID (defaults to latest)."),
):
    conn = _conn()
    proj = _lookup_project(conn, project)

    if session_id is None:
        row = conn.execute(
            "SELECT id FROM sessions WHERE project_id = ? AND ended_at IS NULL "
            "ORDER BY id DESC LIMIT 1",
            (proj.id,),
        ).fetchone()
        if not row:
            console.print("[red]No open session found.[/red]")
            conn.close()
            raise typer.Exit(code=1)
        session_id = row["id"]

    now = datetime.now(timezone.utc).isoformat()
    conn.execute("UPDATE sessions SET ended_at = ? WHERE id = ?", (now, session_id))
    conn.commit()
    console.print(f"[green]Session {session_id} ended.[/green]")
    conn.close()


@session_app.command("list")
def session_list(
    project: str = typer.Argument(..., help="Project name."),
):
    conn = _conn()
    proj = _lookup_project(conn, project)

    rows = conn.execute(
        "SELECT * FROM sessions WHERE project_id = ? ORDER BY id",
        (proj.id,),
    ).fetchall()
    conn.close()

    if not rows:
        console.print("No sessions found.")
        return

    table = Table(title=f"Sessions for '{project}'")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="bold")
    table.add_column("Location")
    table.add_column("Notes")
    table.add_column("Started")
    table.add_column("Ended")

    for row in rows:
        sess = _row_to_session(row)
        table.add_row(
            str(sess.id),
            sess.title,
            sess.location or "",
            sess.notes or "",
            sess.started_at,
            sess.ended_at or "(open)",
        )

    console.print(table)


# Contribution commands


@app.command("add")
def add_contribution(
    project: str = typer.Argument(..., help="Project name."),
    contributor: str = typer.Argument(..., help="Contributor name."),
    role: str = typer.Argument(..., help="Role (e.g. producer, engineer, performer)."),
    description: str = typer.Argument(..., help="What they did."),
    session: int = typer.Option(..., help="Session ID."),
    split: Optional[float] = typer.Option(None, help="Ownership split percentage."),
):
    conn = _conn()

    proj = _lookup_project(conn, project)

    sess = conn.execute("SELECT id FROM sessions WHERE id = ?", (session,)).fetchone()
    if not sess:
        console.print(f"[red]Session {session} not found.[/red]")
        conn.close()
        raise typer.Exit(code=1)

    # Get previous hash (last entry in the global chain).
    last = conn.execute(
        "SELECT hash FROM contributions ORDER BY seq DESC LIMIT 1"
    ).fetchone()
    prev_hash = last["hash"] if last else GENESIS_HASH

    now = datetime.now(timezone.utc).isoformat()

    # We need the seq number before computing the hash. SQLite AUTOINCREMENT
    # guarantees the next value, but we must insert to get it. Instead, we
    # compute what the next seq will be, hash it, then insert atomically.
    last_seq_row = conn.execute("SELECT MAX(seq) as m FROM contributions").fetchone()
    next_seq = (last_seq_row["m"] or 0) + 1

    entry_hash = compute_hash(
        seq=next_seq,
        project_id=proj.id,
        session_id=session,
        contributor=contributor,
        role=role,
        description=description,
        split_pct=split,
        timestamp=now,
        prev_hash=prev_hash,
    )

    conn.execute(
        "INSERT INTO contributions "
        "(project_id, session_id, contributor, role, description, split_pct, "
        "timestamp, prev_hash, hash) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (proj.id, session, contributor, role, description, split, now, prev_hash, entry_hash),
    )
    conn.commit()
    console.print(
        f"[green]Contribution #{next_seq} recorded for {contributor} ({role}).[/green]"
    )
    conn.close()


@app.command("log")
def log_contributions(
    project: Optional[str] = typer.Argument(None, help="Filter by project name."),
    contributor: Optional[str] = typer.Option(None, help="Filter by contributor."),
    role: Optional[str] = typer.Option(None, help="Filter by role."),
    limit: int = typer.Option(50, help="Max entries to show."),
):
    """Show contribution history."""
    conn = _conn()

    query = (
        "SELECT c.seq, p.name as project, c.contributor, c.role, "
        "c.description, c.split_pct, c.timestamp, c.hash "
        "FROM contributions c JOIN projects p ON c.project_id = p.id "
        "WHERE 1=1"
    )
    params: list = []

    if project:
        query += " AND p.name = ?"
        params.append(project)
    if contributor:
        query += " AND c.contributor = ?"
        params.append(contributor)
    if role:
        query += " AND c.role = ?"
        params.append(role)

    query += " ORDER BY c.seq DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        console.print("No contributions found.")
        return

    table = Table(title="Contribution Log")
    table.add_column("#", style="cyan")
    table.add_column("Project")
    table.add_column("Contributor", style="bold")
    table.add_column("Role")
    table.add_column("Description")
    table.add_column("Split %")
    table.add_column("Timestamp")
    table.add_column("Hash", style="dim")

    for row in rows:
        split_str = f"{row['split_pct']:.1f}" if row["split_pct"] is not None else ""
        short_hash = row["hash"][:12] + "..."
        table.add_row(
            str(row["seq"]),
            row["project"],
            row["contributor"],
            row["role"],
            row["description"] or "",
            split_str,
            row["timestamp"],
            short_hash,
        )

    console.print(table)


@app.command("verify")
def verify(
    project: Optional[str] = typer.Argument(None, help="Verify only this project's entries."),
):
    conn = _conn()

    project_id = None
    if project:
        proj = _lookup_project(conn, project)
        project_id = proj.id

    result = verify_chain(conn, project_id=project_id)
    conn.close()

    if result.valid:
        console.print(
            f"[green]Chain verified. {result.entries_checked} entries checked, "
            f"no tampering detected.[/green]"
        )
    else:
        console.print(
            f"[red]Chain broken at seq {result.broken_seq}![/red]\n"
            f"  Expected: {result.expected_hash}\n"
            f"  Found:    {result.actual_hash}"
        )
        raise typer.Exit(code=1)


@app.command("credits")
def credits(
    project: str = typer.Argument(..., help="Project name."),
):
    """Display a formatted credit roll for a project."""
    conn = _conn()
    proj = _lookup_project(conn, project)

    rows = conn.execute(
        "SELECT contributor, role, description, split_pct "
        "FROM contributions WHERE project_id = ? ORDER BY role, contributor",
        (proj.id,),
    ).fetchall()
    conn.close()

    if not rows:
        console.print("No contributions recorded yet.")
        return

    table = Table(title=f"Credits: {proj.name} ({proj.medium})")
    table.add_column("Role", style="bold")
    table.add_column("Contributor")
    table.add_column("Description")
    table.add_column("Split %", justify="right")

    for row in rows:
        split_str = f"{row['split_pct']:.1f}%" if row["split_pct"] is not None else ""
        table.add_row(
            row["role"],
            row["contributor"],
            row["description"] or "",
            split_str,
        )

    console.print(table)


@app.command("export")
def export_cmd(
    project: str = typer.Argument(..., help="Project name."),
    format: str = typer.Option("json", help="Export format: json or csv."),
):
    """Export a project's contributions to JSON or CSV."""
    conn = _conn()
    proj = _lookup_project(conn, project)

    if format == "json":
        output = export_json(conn, proj.id)
    elif format == "csv":
        output = export_csv(conn, proj.id)
    else:
        console.print("[red]Format must be 'json' or 'csv'.[/red]")
        conn.close()
        raise typer.Exit(code=1)

    conn.close()
    print(output)


@app.command("roles")
def list_roles():
    """List known roles."""
    conn = _conn()
    rows = conn.execute("SELECT name FROM roles ORDER BY name").fetchall()
    conn.close()

    table = Table(title="Known Roles")
    table.add_column("Role", style="bold")

    for row in rows:
        table.add_row(row["name"])

    console.print(table)


@app.command("summary")
def summary(
    project: str = typer.Argument(..., help="Project name."),
):
    """Show a statistical summary for a project."""
    conn = _conn()
    proj = _lookup_project(conn, project)

    contrib_count = conn.execute(
        "SELECT COUNT(*) as c FROM contributions WHERE project_id = ?",
        (proj.id,),
    ).fetchone()["c"]

    session_count = conn.execute(
        "SELECT COUNT(*) as c FROM sessions WHERE project_id = ?",
        (proj.id,),
    ).fetchone()["c"]

    unique_contributors = conn.execute(
        "SELECT COUNT(DISTINCT contributor) as c FROM contributions WHERE project_id = ?",
        (proj.id,),
    ).fetchone()["c"]

    unique_roles = conn.execute(
        "SELECT COUNT(DISTINCT role) as c FROM contributions WHERE project_id = ?",
        (proj.id,),
    ).fetchone()["c"]

    total_split = conn.execute(
        "SELECT COALESCE(SUM(split_pct), 0) as s FROM contributions WHERE project_id = ?",
        (proj.id,),
    ).fetchone()["s"]

    result = verify_chain(conn, project_id=proj.id)
    conn.close()

    chain_status = "intact" if result.valid else f"BROKEN at seq {result.broken_seq}"

    table = Table(title=f"Summary: {proj.name}")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Medium", proj.medium)
    table.add_row("Created", proj.created_at)
    table.add_row("Sessions", str(session_count))
    table.add_row("Contributions", str(contrib_count))
    table.add_row("Unique contributors", str(unique_contributors))
    table.add_row("Unique roles", str(unique_roles))
    table.add_row("Total split allocated", f"{total_split:.1f}%")
    table.add_row("Chain status", chain_status)

    console.print(table)


def main():
    app()


if __name__ == "__main__":
    main()
