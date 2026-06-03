"""Tests for the dataclass models and their helper methods."""

from ledger.models import Contribution, Project, Session


class TestProject:
    def test_str_representation(self):
        p = Project(id=1, name="My Album", medium="music", created_at="2026-01-01T00:00:00+00:00")
        assert str(p) == "My Album (music)"

    def test_fields(self):
        p = Project(id=5, name="Film", medium="film", created_at="2026-06-01T12:00:00+00:00")
        assert p.id == 5
        assert p.name == "Film"
        assert p.medium == "film"


class TestSession:
    def test_is_open_true(self):
        s = Session(
            id=1, project_id=1, title="Day 1", location="Studio A",
            started_at="2026-01-01T00:00:00+00:00", ended_at=None, notes=None,
        )
        assert s.is_open is True

    def test_is_open_false(self):
        s = Session(
            id=1, project_id=1, title="Day 1", location=None,
            started_at="2026-01-01T00:00:00+00:00",
            ended_at="2026-01-01T18:00:00+00:00", notes="Good session",
        )
        assert s.is_open is False

    def test_str_open(self):
        s = Session(
            id=3, project_id=1, title="Tracking", location=None,
            started_at="2026-01-01T00:00:00+00:00", ended_at=None, notes=None,
        )
        assert "open" in str(s)
        assert "Tracking" in str(s)

    def test_str_closed(self):
        s = Session(
            id=3, project_id=1, title="Tracking", location=None,
            started_at="2026-01-01T00:00:00+00:00",
            ended_at="2026-01-01T18:00:00+00:00", notes=None,
        )
        assert "closed" in str(s)


class TestContribution:
    def test_short_hash(self):
        c = Contribution(
            seq=1, project_id=1, session_id=1, contributor="Alice",
            role="producer", description="Produced", split_pct=50.0,
            timestamp="2026-01-01T00:00:00+00:00",
            prev_hash="0" * 64,
            hash="abcdef123456789000aabbccdd",
        )
        assert c.short_hash == "abcdef123456"
        assert len(c.short_hash) == 12

    def test_str_with_split(self):
        c = Contribution(
            seq=7, project_id=1, session_id=1, contributor="Bob",
            role="engineer", description="Mixed", split_pct=30.0,
            timestamp="2026-01-01T00:00:00+00:00",
            prev_hash="0" * 64, hash="a" * 64,
        )
        result = str(c)
        assert "#7" in result
        assert "Bob" in result
        assert "engineer" in result
        assert "30.0%" in result

    def test_str_without_split(self):
        c = Contribution(
            seq=1, project_id=1, session_id=1, contributor="Carol",
            role="performer", description="Sang", split_pct=None,
            timestamp="2026-01-01T00:00:00+00:00",
            prev_hash="0" * 64, hash="b" * 64,
        )
        result = str(c)
        assert "#1" in result
        assert "Carol" in result
        assert "%" not in result
