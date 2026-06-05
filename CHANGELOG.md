# Changelog

All notable changes to ledger are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0]

### Added
- Project management: create, list, and delete projects with name and medium type (music, film, art, other).
- Session tracking: start and end sessions tied to a project, with title, location, notes, and timestamps.
- Contribution recording: append contributions with contributor name, role, description, and optional split percentage, linked to a project and session.
- SHA-256 hash chain: every contribution stores a hash computed from canonical JSON of its fields plus the previous entry's hash, providing tamper evidence.
- Chain verification: `verify` command walks the full chain (or filters by project), recomputes every hash, and reports the first broken link.
- Credit roll display: `credits` command renders a Rich table grouping contributors by role with split percentages.
- Project summary: `summary` command shows statistics including session count, contribution count, unique contributors, unique roles, total split allocated, and chain integrity status.
- Contribution log: `log` command with optional filters by project, contributor, role, and limit.
- JSON and CSV export of a project's contributions to stdout.
- Pre-seeded role reference table with 13 roles (producer, director, composer, engineer, performer, editor, cinematographer, mixer, writer, artist, designer, animator, other).
- SQLite persistence with WAL mode at ~/.ledger/ledger.db.
- Test suite covering models, hash chain math, database operations, CLI commands, and export formatting.
- CI workflow running pytest on Python 3.10, 3.11, and 3.12.
