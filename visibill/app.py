from __future__ import annotations

from collections.abc import Sequence
from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import DataTable, Footer, Header, Input, Static

from visibill.filtering import (
    FilterParseError,
    has_structured_operator,
    matches_filter,
    parse_filter,
)
from visibill.logs import DetailField, EventDetail, LogEvent, build_event_detail


FILTER_DEBOUNCE_SECONDS = 0.2


class DetailScreen(Screen[None]):
    BINDINGS = [Binding("escape", "close_detail", "Back")]

    CSS = """
    Screen {
        layout: vertical;
    }

    #detail-body {
        height: 1fr;
        padding: 1 2;
        overflow: auto;
    }

    #detail-title {
        height: auto;
        text-style: bold;
    }

    #detail-summary,
    #detail-sections,
    #detail-raw {
        height: auto;
        margin-top: 1;
    }
    """

    def __init__(self, detail: EventDetail) -> None:
        super().__init__()
        self.detail = detail

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="detail-body"):
            yield Static(id="detail-title")
            yield Static(id="detail-summary")
            yield Static(id="detail-sections")
            yield Static("Raw JSON", classes="section-title")
            yield Static(id="detail-raw")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#detail-title", Static).update(self.render_title())
        self.query_one("#detail-summary", Static).update(self.render_summary())
        self.query_one("#detail-sections", Static).update(self.render_sections())
        self.query_one("#detail-raw", Static).update(self.render_raw())

    def action_close_detail(self) -> None:
        self.app.pop_screen()

    def render_title(self) -> Text:
        title = Text(self.detail.title or "Event detail")
        title.stylize("bold")
        return title

    def render_summary(self) -> Text:
        text = Text()
        text.append("Summary\n", style="bold")
        for label, value in self.detail.summary:
            text.append(label, style="bold cyan")
            text.append(": ")
            text.append(value)
            text.append("\n")
        return text

    def render_sections(self) -> Text:
        text = Text()
        if not self.detail.sections:
            text.append("No structured fields found.\n", style="dim")
            return text

        for section in self.detail.sections:
            text.append(f"{section.title}\n", style="bold")
            self.append_fields(text, section.fields)
            text.append("\n")
        return text

    def render_raw(self) -> Text:
        return Text(self.detail.raw_json)

    def append_fields(
        self, text: Text, fields: list[DetailField], indent: int = 1
    ) -> None:
        prefix = "  " * indent
        for field in fields:
            if field.children:
                text.append(f"{prefix}{field.key}\n", style="bold")
                self.append_fields(text, field.children, indent + 1)
                continue

            text.append(f"{prefix}{field.key}", style="bold")
            text.append(": ")
            text.append(f"{field.value}\n")


class VisibillApp(App[None]):
    """Minimal JSONL log explorer."""

    TITLE = "Visibill"
    SUB_TITLE = "JSONL log explorer"
    THEME = "catppuccin-mocha"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("/", "focus_filter", "Filter"),
        Binding("escape", "blur_filter", "Leave Filter"),
        Binding("enter", "open_detail", "Open Selected"),
    ]

    CSS = """
    Screen {
        layout: vertical;
    }

    #body {
        width: 1fr;
        height: 1fr;
        layout: vertical;
    }

    #table {
        height: 1fr;
    }

    #controls {
        height: auto;
        padding: 0 1 1 1;
    }

    #filter {
        margin-bottom: 1;
    }

    #status {
        height: auto;
    }
    """

    def __init__(self, events: Sequence[LogEvent] | None = None) -> None:
        super().__init__()
        self.all_events: list[LogEvent] = list(events or [])
        self.visible_events: list[LogEvent] = list(self.all_events)
        self.parse_failures = sum(1 for event in self.all_events if event.parse_error)
        self.filter_mode = "text"
        self.filter_error: str | None = None
        self.pending_filter_value = ""
        self.filter_debounce_timer: Timer | None = None
        self.filter_debounce_request = 0

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="body"):
            yield DataTable(id="table")
        with Vertical(id="controls"):
            yield Input(placeholder="Filter rows (/ to focus)", id="filter")
            yield Static(id="status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns("#", "Timestamp", "Level", "Source", "Message")
        self.refresh_table()
        table.focus()

    def action_focus_filter(self) -> None:
        self.query_one(Input).focus()

    def action_blur_filter(self) -> None:
        if self.query_one(Input).has_focus:
            self.query_one(DataTable).focus()

    @on(Input.Changed, "#filter")
    def handle_filter_changed(self, event: Input.Changed) -> None:
        self.pending_filter_value = event.value
        self.filter_debounce_request += 1
        request = self.filter_debounce_request

        if self.filter_debounce_timer is not None:
            self.filter_debounce_timer.stop()

        self.filter_debounce_timer = self.set_timer(
            FILTER_DEBOUNCE_SECONDS,
            lambda: self.apply_pending_filter(request),
        )

    def apply_pending_filter(self, request: int | None = None) -> None:
        if request is not None and request != self.filter_debounce_request:
            return

        self.filter_debounce_timer = None
        self.apply_filter(self.pending_filter_value)

    def apply_filter(self, raw_filter: str) -> None:
        raw_filter = raw_filter.strip()
        self.filter_error = None
        self.filter_mode = "text"

        if not raw_filter:
            self.visible_events = list(self.all_events)
        elif not has_structured_operator(raw_filter):
            query = raw_filter.lower()
            self.visible_events = [
                entry for entry in self.all_events if query in entry.filter_text
            ]
        else:
            self.filter_mode = "query"
            try:
                query = parse_filter(raw_filter)
            except FilterParseError as exc:
                self.filter_error = str(exc)
                self.visible_events = []
            else:
                self.visible_events = [
                    entry for entry in self.all_events if matches_filter(entry, query)
                ]
        self.refresh_table()

    @on(DataTable.RowHighlighted, "#table")
    def handle_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        del event

    @on(DataTable.RowSelected, "#table")
    def handle_row_selected(self, event: DataTable.RowSelected) -> None:
        self.open_detail_for_index(event.cursor_row)

    def action_open_detail(self) -> None:
        table = self.query_one(DataTable)
        self.open_detail_for_index(table.cursor_row)

    def open_detail_for_index(self, index: int) -> None:
        if 0 <= index < len(self.visible_events):
            self.push_screen(
                DetailScreen(build_event_detail(self.visible_events[index]))
            )

    def refresh_table(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        if self.visible_events:
            table.add_rows(
                [
                    (
                        str(event.index),
                        event.timestamp,
                        event.level,
                        event.source,
                        event.message,
                    )
                    for event in self.visible_events
                ]
            )
            table.move_cursor(row=0, column=0)
        self.update_status()

    def update_status(self) -> None:
        parts = [
            f"total={len(self.all_events)}",
            f"visible={len(self.visible_events)}",
            f"parse_failures={self.parse_failures}",
            f"filter_mode={self.filter_mode}",
        ]
        if self.filter_error:
            parts.append(f"filter_error={self.filter_error}")
        self.query_one("#status", Static).update(" ".join(parts))
