"""Tests for the Typer CLI commands."""

import json

from typer.testing import CliRunner

from ledger.cli import app

runner = CliRunner()


class TestProjectCommands:
    def test_create_project(self, cli_db):
        result = runner.invoke(app, ["project", "create", "MyAlbum", "--medium", "music"])
        assert result.exit_code == 0
        assert "created" in result.output.lower()

    def test_create_duplicate_project(self, cli_db):
        runner.invoke(app, ["project", "create", "Dup"])
        result = runner.invoke(app, ["project", "create", "Dup"])
        assert result.exit_code != 0

    def test_list_projects(self, cli_db):
        runner.invoke(app, ["project", "create", "Alpha", "--medium", "film"])
        runner.invoke(app, ["project", "create", "Beta", "--medium", "art"])
        result = runner.invoke(app, ["project", "list"])
        assert result.exit_code == 0
        assert "Alpha" in result.output
        assert "Beta" in result.output

    def test_list_empty(self, cli_db):
        result = runner.invoke(app, ["project", "list"])
        assert result.exit_code == 0
        assert "No projects found" in result.output

    def test_invalid_medium(self, cli_db):
        result = runner.invoke(app, ["project", "create", "Bad", "--medium", "sculpture"])
        assert result.exit_code != 0

    def test_delete_project_force(self, cli_db):
        runner.invoke(app, ["project", "create", "ToDelete", "--medium", "music"])
        runner.invoke(app, ["session", "start", "ToDelete", "S1"])
        runner.invoke(
            app,
            ["add", "ToDelete", "Alice", "producer", "Produced", "--session", "1"],
        )
        result = runner.invoke(app, ["project", "delete", "ToDelete", "--force"])
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()
        # Project should be gone.
        list_result = runner.invoke(app, ["project", "list"])
        assert "ToDelete" not in list_result.output

    def test_delete_missing_project(self, cli_db):
        result = runner.invoke(app, ["project", "delete", "Nonexistent", "--force"])
        assert result.exit_code != 0

    def test_default_medium(self, cli_db):
        result = runner.invoke(app, ["project", "create", "DefaultMedium"])
        assert result.exit_code == 0
        assert "created" in result.output.lower()


class TestSessionCommands:
    def _create_project(self):
        runner.invoke(app, ["project", "create", "Proj", "--medium", "music"])

    def test_start_session(self, cli_db):
        self._create_project()
        result = runner.invoke(app, ["session", "start", "Proj", "Day 1", "--location", "Studio A"])
        assert result.exit_code == 0
        assert "started" in result.output.lower()

    def test_start_session_with_notes(self, cli_db):
        self._create_project()
        result = runner.invoke(
            app,
            ["session", "start", "Proj", "Day 1", "--notes", "First tracking day"],
        )
        assert result.exit_code == 0
        assert "started" in result.output.lower()

    def test_start_session_missing_project(self, cli_db):
        result = runner.invoke(app, ["session", "start", "NoSuch", "Day 1"])
        assert result.exit_code != 0

    def test_end_session(self, cli_db):
        self._create_project()
        runner.invoke(app, ["session", "start", "Proj", "Day 1"])
        result = runner.invoke(app, ["session", "end", "Proj"])
        assert result.exit_code == 0
        assert "ended" in result.output.lower()

    def test_end_no_open_session(self, cli_db):
        self._create_project()
        result = runner.invoke(app, ["session", "end", "Proj"])
        assert result.exit_code != 0

    def test_list_sessions(self, cli_db):
        self._create_project()
        runner.invoke(app, ["session", "start", "Proj", "Day 1"])
        runner.invoke(app, ["session", "start", "Proj", "Day 2"])
        result = runner.invoke(app, ["session", "list", "Proj"])
        assert result.exit_code == 0
        assert "Day 1" in result.output
        assert "Day 2" in result.output

    def test_list_sessions_empty(self, cli_db):
        self._create_project()
        result = runner.invoke(app, ["session", "list", "Proj"])
        assert result.exit_code == 0
        assert "No sessions found" in result.output


class TestContributionCommands:
    def _setup(self):
        runner.invoke(app, ["project", "create", "Album", "--medium", "music"])
        runner.invoke(app, ["session", "start", "Album", "Tracking"])

    def test_add_contribution(self, cli_db):
        self._setup()
        result = runner.invoke(
            app,
            ["add", "Album", "Alice", "producer", "Produced the track",
             "--session", "1", "--split", "50.0"],
        )
        assert result.exit_code == 0
        assert "recorded" in result.output.lower()

    def test_add_missing_project(self, cli_db):
        result = runner.invoke(
            app,
            ["add", "NoSuch", "Alice", "producer", "Did stuff", "--session", "1"],
        )
        assert result.exit_code != 0

    def test_add_missing_session(self, cli_db):
        runner.invoke(app, ["project", "create", "Proj", "--medium", "music"])
        result = runner.invoke(
            app,
            ["add", "Proj", "Alice", "producer", "Did stuff", "--session", "999"],
        )
        assert result.exit_code != 0

    def test_add_without_split(self, cli_db):
        self._setup()
        result = runner.invoke(
            app,
            ["add", "Album", "Alice", "performer", "Sang", "--session", "1"],
        )
        assert result.exit_code == 0
        assert "recorded" in result.output.lower()

    def test_log_contributions(self, cli_db):
        self._setup()
        runner.invoke(
            app,
            ["add", "Album", "Alice", "producer", "Produced",
             "--session", "1", "--split", "60.0"],
        )
        runner.invoke(
            app,
            ["add", "Album", "Bob", "engineer", "Mixed",
             "--session", "1", "--split", "40.0"],
        )
        result = runner.invoke(app, ["log", "Album"])
        assert result.exit_code == 0
        assert "Alice" in result.output
        assert "Bob" in result.output

    def test_log_filter_by_contributor(self, cli_db):
        self._setup()
        runner.invoke(
            app,
            ["add", "Album", "Alice", "producer", "Produced", "--session", "1"],
        )
        runner.invoke(
            app,
            ["add", "Album", "Bob", "engineer", "Mixed", "--session", "1"],
        )
        result = runner.invoke(app, ["log", "--contributor", "Alice"])
        assert result.exit_code == 0
        assert "Alice" in result.output

    def test_log_filter_by_role(self, cli_db):
        self._setup()
        runner.invoke(
            app,
            ["add", "Album", "Alice", "producer", "Produced", "--session", "1"],
        )
        result = runner.invoke(app, ["log", "--role", "producer"])
        assert result.exit_code == 0
        assert "producer" in result.output

    def test_log_empty(self, cli_db):
        result = runner.invoke(app, ["log"])
        assert result.exit_code == 0
        assert "No contributions found" in result.output


class TestVerifyCommand:
    def _setup_with_entries(self):
        runner.invoke(app, ["project", "create", "V", "--medium", "music"])
        runner.invoke(app, ["session", "start", "V", "S1"])
        runner.invoke(
            app,
            ["add", "V", "Alice", "producer", "Produced", "--session", "1"],
        )
        runner.invoke(
            app,
            ["add", "V", "Bob", "engineer", "Mixed", "--session", "1"],
        )

    def test_verify_clean_chain(self, cli_db):
        self._setup_with_entries()
        result = runner.invoke(app, ["verify"])
        assert result.exit_code == 0
        assert "verified" in result.output.lower()

    def test_verify_empty(self, cli_db):
        result = runner.invoke(app, ["verify"])
        assert result.exit_code == 0
        assert "0 entries" in result.output

    def test_verify_by_project(self, cli_db):
        self._setup_with_entries()
        result = runner.invoke(app, ["verify", "V"])
        assert result.exit_code == 0
        assert "verified" in result.output.lower()

    def test_verify_missing_project(self, cli_db):
        result = runner.invoke(app, ["verify", "Nonexistent"])
        assert result.exit_code != 0


class TestCreditsCommand:
    def test_credits_display(self, cli_db):
        runner.invoke(app, ["project", "create", "Film", "--medium", "film"])
        runner.invoke(app, ["session", "start", "Film", "Shoot"])
        runner.invoke(
            app,
            ["add", "Film", "Alice", "director", "Directed",
             "--session", "1", "--split", "50.0"],
        )
        result = runner.invoke(app, ["credits", "Film"])
        assert result.exit_code == 0
        assert "Alice" in result.output
        assert "director" in result.output

    def test_credits_missing_project(self, cli_db):
        result = runner.invoke(app, ["credits", "Nope"])
        assert result.exit_code != 0

    def test_credits_empty_project(self, cli_db):
        runner.invoke(app, ["project", "create", "Empty", "--medium", "music"])
        result = runner.invoke(app, ["credits", "Empty"])
        assert result.exit_code == 0
        assert "No contributions recorded" in result.output


class TestExportCommand:
    def _setup(self):
        runner.invoke(app, ["project", "create", "Exp", "--medium", "music"])
        runner.invoke(app, ["session", "start", "Exp", "S1"])
        runner.invoke(
            app,
            ["add", "Exp", "Alice", "producer", "Produced",
             "--session", "1", "--split", "100.0"],
        )

    def test_export_json(self, cli_db):
        self._setup()
        result = runner.invoke(app, ["export", "Exp", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["contributor"] == "Alice"

    def test_export_csv(self, cli_db):
        self._setup()
        result = runner.invoke(app, ["export", "Exp", "--format", "csv"])
        assert result.exit_code == 0
        assert "contributor" in result.output
        assert "Alice" in result.output

    def test_export_missing_project(self, cli_db):
        result = runner.invoke(app, ["export", "Nope"])
        assert result.exit_code != 0

    def test_export_invalid_format(self, cli_db):
        self._setup()
        result = runner.invoke(app, ["export", "Exp", "--format", "xml"])
        assert result.exit_code != 0


class TestRolesCommand:
    def test_list_roles(self, cli_db):
        result = runner.invoke(app, ["roles"])
        assert result.exit_code == 0
        assert "producer" in result.output
        assert "engineer" in result.output
        assert "performer" in result.output


class TestSummaryCommand:
    def test_summary_with_data(self, cli_db):
        runner.invoke(app, ["project", "create", "Sum", "--medium", "music"])
        runner.invoke(app, ["session", "start", "Sum", "S1"])
        runner.invoke(
            app,
            ["add", "Sum", "Alice", "producer", "Produced",
             "--session", "1", "--split", "60.0"],
        )
        runner.invoke(
            app,
            ["add", "Sum", "Bob", "engineer", "Mixed",
             "--session", "1", "--split", "40.0"],
        )
        result = runner.invoke(app, ["summary", "Sum"])
        assert result.exit_code == 0
        assert "Sum" in result.output
        assert "2" in result.output  # 2 contributions
        assert "intact" in result.output

    def test_summary_empty_project(self, cli_db):
        runner.invoke(app, ["project", "create", "EmptySum", "--medium", "art"])
        result = runner.invoke(app, ["summary", "EmptySum"])
        assert result.exit_code == 0
        assert "0" in result.output

    def test_summary_missing_project(self, cli_db):
        result = runner.invoke(app, ["summary", "Nonexistent"])
        assert result.exit_code != 0
