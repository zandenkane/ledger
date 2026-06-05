"""Integration test proving the core ledger concept: tamper detection via hash chain.

This test exercises the full workflow end-to-end:
  1. Create a project ("test-album")
  2. Start a session
  3. Add 3 contributions with specific splits
  4. Verify all 3 are stored correctly in the database
  5. Verify the hash chain linkage is intact (each entry references the previous hash)
  6. Tamper with one record (change alice's split from 40% to 50%)
  7. Verify the chain is now BROKEN -- proving ledger detects tampering
"""

from typer.testing import CliRunner

from ledger.chain import GENESIS_HASH, verify_chain
from ledger.cli import app
from ledger.db import get_connection

runner = CliRunner()


def test_tamper_detection_full_workflow(cli_db):
    """End-to-end proof that ledger detects database tampering."""

    # -- Step 1: Create the project --
    result = runner.invoke(app, ["project", "create", "test-album", "--medium", "music"])
    assert result.exit_code == 0, f"project create failed: {result.output}"

    # -- Step 2: Start a session (required for contributions) --
    result = runner.invoke(app, ["session", "start", "test-album", "tracking-session"])
    assert result.exit_code == 0, f"session start failed: {result.output}"

    # -- Step 3: Add 3 contributions --
    result = runner.invoke(
        app,
        ["add", "test-album", "alice", "guitar", "Lead guitar",
         "--session", "1", "--split", "40.0"],
    )
    assert result.exit_code == 0, f"add alice failed: {result.output}"

    result = runner.invoke(
        app,
        ["add", "test-album", "bob", "drums", "Drum tracking",
         "--session", "1", "--split", "35.0"],
    )
    assert result.exit_code == 0, f"add bob failed: {result.output}"

    result = runner.invoke(
        app,
        ["add", "test-album", "charlie", "mixing", "Final mix",
         "--session", "1", "--split", "25.0"],
    )
    assert result.exit_code == 0, f"add charlie failed: {result.output}"

    # -- Step 4: Verify all 3 contributions are in the database --
    conn = get_connection(cli_db)
    rows = conn.execute(
        "SELECT seq, contributor, role, split_pct, prev_hash, hash "
        "FROM contributions ORDER BY seq"
    ).fetchall()

    assert len(rows) == 3, f"Expected 3 contributions, got {len(rows)}"

    assert rows[0]["contributor"] == "alice"
    assert rows[0]["role"] == "guitar"
    assert rows[0]["split_pct"] == 40.0

    assert rows[1]["contributor"] == "bob"
    assert rows[1]["role"] == "drums"
    assert rows[1]["split_pct"] == 35.0

    assert rows[2]["contributor"] == "charlie"
    assert rows[2]["role"] == "mixing"
    assert rows[2]["split_pct"] == 25.0

    # -- Step 5: Verify the hash chain linkage is intact --
    # Each entry's prev_hash must reference the hash of the entry before it.
    # The first entry references GENESIS_HASH (all zeros).
    assert rows[0]["prev_hash"] == GENESIS_HASH, (
        f"First entry should reference genesis hash, got {rows[0]['prev_hash']}"
    )
    assert rows[1]["prev_hash"] == rows[0]["hash"], (
        "Second entry's prev_hash should equal first entry's hash"
    )
    assert rows[2]["prev_hash"] == rows[1]["hash"], (
        "Third entry's prev_hash should equal second entry's hash"
    )

    # verify_chain should also confirm integrity
    chain_result = verify_chain(conn, project_id=1)
    assert chain_result.valid is True
    assert chain_result.entries_checked == 3

    # Also verify via the CLI command
    verify_cli = runner.invoke(app, ["verify", "test-album"])
    assert verify_cli.exit_code == 0
    assert "verified" in verify_cli.output.lower()

    # -- Step 6: Tamper with alice's split (change 40% to 50%) --
    conn.execute(
        "UPDATE contributions SET split_pct = 50.0 WHERE contributor = 'alice'"
    )
    conn.commit()

    # Confirm the tamper took effect in the raw data
    tampered = conn.execute(
        "SELECT split_pct FROM contributions WHERE contributor = 'alice'"
    ).fetchone()
    assert tampered["split_pct"] == 50.0, "Tamper did not apply"

    # -- Step 7: Verify the chain is now BROKEN --
    # This is the whole point of ledger: the stored hash was computed with
    # split_pct=40.0, but the field now says 50.0. Recomputing the hash
    # from the stored fields will produce a different value.
    broken_result = verify_chain(conn, project_id=1)
    assert broken_result.valid is False, (
        "Chain should be broken after tampering, but verify_chain says it is valid"
    )
    assert broken_result.broken_seq == 1, (
        f"Tamper was on seq 1 (alice), but broken_seq reported {broken_result.broken_seq}"
    )

    # The CLI verify command should also report the breakage
    verify_broken = runner.invoke(app, ["verify", "test-album"])
    assert verify_broken.exit_code != 0, (
        "CLI verify should exit non-zero when chain is broken"
    )
    assert "broken" in verify_broken.output.lower(), (
        f"CLI verify output should mention 'broken', got: {verify_broken.output}"
    )

    conn.close()
