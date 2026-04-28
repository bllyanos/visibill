# Visibill Implementation Plan

## Goal

Build a simple Textual-based JSON Lines log explorer that can read piped input, for example:

```bash
tail -n 10000 app.log.jsonl | visibill
```

The first version should optimize for fast navigation and inspection of recent structured logs rather than full log management.

## Textual Notes

Research against current Textual docs suggests these project choices:

- Use a normal `App` with `compose()` to build the screen structure.
- Use `Header` and `Footer` so key bindings are visible and discoverable.
- Avoid recomposing stateful widgets like `DataTable`; update them in place.
- Use app-level bindings and focused widgets for keyboard-driven workflows.
- Keep long-running input parsing off the UI path by using a background worker or batched updates.

## MVP Scope

The MVP should support:

- Reading newline-delimited input from `stdin`.
- Parsing each line as JSON when possible.
- Preserving unparseable lines as raw text with an error marker.
- Showing a table of recent events.
- Showing details for the selected event.
- Filtering rows with a plain text query.
- Navigating fully by keyboard.

The MVP should not yet include:

- Live follow mode for an indefinitely open pipe.
- Multi-file loading.
- JSONPath or jq-like querying.
- Saved views or bookmarks.
- Export features.

## User Experience

Recommended layout:

- Top: `Header` with app title.
- Main left: `DataTable` with one row per log event.
- Main right: detail pane for the selected event.
- Bottom: filter input plus `Footer` for bindings.

Recommended default columns:

- Row number
- Timestamp
- Level
- Logger or service
- Message summary

Column values should be derived heuristically from common keys such as:

- `timestamp`, `time`, `ts`
- `level`, `severity`, `log_level`
- `logger`, `service`, `component`, `name`
- `message`, `msg`, `event`

If keys are missing, show an empty string rather than failing.

## Input Model

Assume the first implementation reads from `stdin` only.

Parsing flow:

1. Read all incoming lines from `stdin`.
2. For each line, strip the trailing newline.
3. Attempt `json.loads(line)`.
4. If the result is a JSON object, store it as the event payload.
5. If parsing fails or the value is not an object, store a fallback event with:
   - raw line
   - parse error flag
   - synthetic message

Suggested internal model per event:

```python
@dataclass
class LogEvent:
    index: int
    raw_line: str
    payload: dict[str, object] | None
    parse_error: str | None
    timestamp: str
    level: str
    source: str
    message: str
```

Keep the normalized fields on the model so the UI does not repeatedly re-derive them.

## UI Components

Suggested first-pass widget structure:

- `VisibillApp`
- `DataTable` for results
- `Pretty` or `Static` for selected JSON detail
- `Input` for filter text
- Optional status line widget for counts and parse errors

Behavior:

- Up and down move selection in the table.
- The detail pane updates when selection changes.
- `/` focuses the filter input.
- `escape` clears filter focus.
- `q` quits.

## Filtering Strategy

Start with a simple case-insensitive substring match across:

- normalized message
- normalized level
- normalized source
- raw line

Implementation approach:

- Keep `all_events` as the full parsed list.
- Build `visible_events` from the current filter.
- Refill the `DataTable` from `visible_events` in batches when the filter changes.

This is simple, predictable, and enough for the MVP.

## Performance Approach

For `tail -n 10000`, a straightforward in-memory model is acceptable.

Recommended guardrails:

- Batch table population instead of per-line full refreshes.
- Avoid recomposing the table widget.
- Keep normalized display strings cached on each event.
- Defer expensive pretty rendering until a row is selected.

If performance becomes an issue later, the first upgrade should be incremental ingestion plus viewport-aware rendering.

## Delivery Steps

1. Replace the placeholder app with a real `VisibillApp` layout.
2. Add `stdin` ingestion and JSONL parsing utilities.
3. Add the `LogEvent` model and field normalization helpers.
4. Populate a `DataTable` with parsed events.
5. Add selection handling and a detail pane.
6. Add filter input and row filtering.
7. Add status text for total rows, visible rows, and parse failures.
8. Test with mixed valid and invalid JSONL input.

## Acceptance Criteria

The first implementation is complete when:

- `tail -n 10000 sample.jsonl | visibill` launches successfully.
- The table renders rows from piped input.
- Arrow keys change selection.
- The detail pane shows the selected event payload or raw line.
- Typing a filter reduces the visible rows.
- Invalid JSON lines do not crash the app.

## Nice Next Steps

- Support follow mode for a still-open pipe.
- Add column sorting.
- Add level-based color styling.
- Add a toggle between pretty JSON and raw line views.
- Add a compact help screen.
- Support reading from file paths as well as `stdin`.
