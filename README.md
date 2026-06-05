# ledger

![CI](https://github.com/zandenkane/ledger/actions/workflows/ci.yml/badge.svg)

I played guitar on three tracks and my name wasn't on any of them. Never again.

That's why this exists. `ledger` is a CLI tool that records who did what on a creative project, when they did it, and what percentage of the pie they own. Every entry goes into a SQLite database and gets chained together with SHA-256 hashes. If somebody goes back and edits a record after the fact, `ledger verify` catches it and tells you exactly where the chain broke.

Music, film, art, whatever. If people collaborate on something and credits matter, this is the receipt.

## Install

```bash
git clone https://github.com/zandenkane/ledger.git
cd ledger
pip install -e ".[dev]"
```

Python 3.10 or newer.

## How it works

You create a project, start sessions within that project, and log contributions against those sessions. Each contribution records the person's name, their role, what they did, and optionally their ownership split. The whole thing is append-only with hash chaining, so nobody can quietly rewrite history.

## Usage

### Create a project

```bash
ledger project create "My Album" --medium music
ledger project list
```

Medium can be `music`, `film`, `art`, or `other`.

### Sessions

Sessions are blocks of time tied to a project. A studio day, a shoot, whatever.

```bash
ledger session start "My Album" "Tracking day 1" --location "Studio A"
ledger session start "My Album" "Overdubs" --location "Studio B" --notes "Guitar and vocals"
ledger session list "My Album"
ledger session end "My Album"
```

### Log contributions

This is the whole point. Who did what.

```bash
ledger add "My Album" "Alice" producer "Produced the track" --session 1 --split 50.0
ledger add "My Album" "Bob" engineer "Mixed and mastered" --session 1 --split 30.0
ledger add "My Album" "Carol" performer "Lead vocals" --session 1 --split 20.0
```

### View the log

```bash
ledger log "My Album"
ledger log --contributor Alice
ledger log --role producer --limit 10
```

### Verify the chain

This is where it gets real. If anyone touched a past record, this catches it.

```bash
ledger verify
ledger verify "My Album"
```

It walks every entry, recomputes the hash from the stored fields, and flags the first place where the math stops adding up.

### Credits

```bash
ledger credits "My Album"
```

Renders a table of everyone who worked on the project, grouped by role, with split percentages.

### Summary

```bash
ledger summary "My Album"
```

Shows stats for a project: session count, contribution count, unique contributors, unique roles, total split allocated, and whether the chain is intact.

### Export

```bash
ledger export "My Album" --format json
ledger export "My Album" --format csv
```

Prints to stdout. Redirect to a file if you want to keep it.

### Delete a project

```bash
ledger project delete "My Album" --force
```

Without `--force` it asks for confirmation first.

### List known roles

```bash
ledger roles
```

Pre-seeded roles: producer, director, composer, engineer, performer, editor, cinematographer, mixer, writer, artist, designer, animator, other. You can use any string you want though.

## Data storage

Everything lives in a single SQLite file at `~/.ledger/ledger.db`, created automatically on first use. WAL mode is on.

## Running tests

```bash
pytest -v
```

Tests use temp databases. Your real data stays untouched.

## Limitations

- Single user. Concurrent writes from multiple processes rely on SQLite's busy timeout and nothing more.
- Split percentages are recorded but not validated to sum to 100%.
- No authentication. The contributor field is just text.
- No cryptographic signing. This proves records haven't been changed, not who entered them.
- No web UI. Terminal only.

## License

MIT. See [LICENSE](LICENSE).
