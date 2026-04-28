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

## Run

```bash
visibill < sample.log
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
timestamp>='2026-04-28T10:40:00Z'
level=info source~AwsS3Client
ts>='2026-04-13'
```

## Development

```bash
uv run pytest
uv run visibill < sample.log
```
