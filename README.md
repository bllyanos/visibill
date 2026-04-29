# Visibill

Terminal JSONL log explorer built with Textual.

## Features

- Load JSONL events from `stdin`
- Browse rows in a terminal UI
- Filter with plain text or structured queries
- Open an event detail view for the selected row

## Install

```bash
uv sync
```

## Local Install

1. Install `uv` if you do not already have it.
2. Clone this repository and `cd` into it.
3. Create the environment and install dependencies with `uv sync`.
4. Run the app with `uv run visibill < sample.log`.

To install the CLI globally with `uv tool` (**Recommended**):

```bash
uv tool install .
```

If you prefer to install the package into your active environment, use:

```bash
uv pip install .
```

After that, run `visibill` from your shell without `uv run`.

## Run

```bash
visibill < sample.log
visibill --file sample.log
visibill --help
```

## Filtering

- Plain text filters match across the event search text
- Structured filters support `=`, `!=`, `~`, `>`, `>=`, `<`, and `<=`
- Supported fields are `timestamp`, `level`, `source`, `message`, and `raw`
- Aliases: `ts` for `timestamp`, `logger` for `source`, `method` for `source`
- Clear the filter to show all rows again

Examples:

```text
level=error
source~AwsS3Client
message~expiration
message~"document expiration"
timestamp>='2026-04-28T10:40:00Z'
level=info source~AwsS3Client
level=info message~"document expiration"
ts>='2026-04-13'
```

## Development

```bash
uv run pytest
uv run visibill < sample.log
```
