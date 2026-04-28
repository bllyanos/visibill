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
- Structured filters use query operators supported by the app
- Clear the filter to show all rows again

## Development

```bash
uv run pytest
uv run visibill < sample.log
```
