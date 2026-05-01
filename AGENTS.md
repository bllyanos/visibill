# Visibill Agent Notes

## Environment

- **Package manager:** `uv`. Use `uv sync` and `uv run`. Do not use `pip`.
- **Python:** 3.11 (pinned in `.python-version` and `pyproject.toml`).
- **Build:** hatchling. `uv pip install .` or `uv tool install .` for local/global install.

## Running

```bash
# From source
uv run visibill < sample.log
uv run visibill --file sample.log

# Tests (unittest; pytest is NOT installed)
uv run python -m unittest discover -s tests -v
uv run python -m unittest tests.test_filtering
```

> Note: README mentions `uv run pytest`, but pytest is not in `uv.lock` or dependencies. Use `python -m unittest`.

## Architecture

| File | Responsibility |
|------|----------------|
| `visibill/main.py` | CLI entrypoint (`argparse`), file/stdin ingestion, `interactive_stdin()` TTY swap |
| `visibill/app.py` | Textual `App`, `DataTable`, filter debounce (`0.2s`), detail screen |
| `visibill/logs.py` | JSONL parsing, `LogEvent` dataclass, field normalization (`@fields`, `@message`, `@timestamp`) |
| `visibill/filtering.py` | Structured filter parser (`shlex.split`), timestamp comparisons, field aliases |

## Critical Quirks

- **TTY swap:** `main.py` swaps `sys.stdin` to the controlling terminal (`os.ctermid()`) when input is piped, because Textual requires a TTY for keyboard input. The original stdin is restored on exit.
- **Filter parsing:** Uses `shlex.split()`, so quoted values with spaces work: `message~"document expiration"`. Unmatched quotes raise `FilterParseError`.
- **Timestamp comparisons:** Only `timestamp` field supports `>`, `>=`, `<`, `<=`. Date-only strings (no `T`) are treated as prefix filters, not parsed to `datetime`.
- **Field aliases:** `ts` → `timestamp`, `logger` / `method` → `source`.
- **Tests depend on `sample.log`:** Tests read `sample.log` from the repo root via `Path(__file__).resolve().parents[1] / "sample.log"`.

## Backlog Workflow

`backlog.yaml` is the source of truth for tasks. See `BACKLOG.md` for schema rules. Do not treat `BACKLOG.md` itself as the task list.
