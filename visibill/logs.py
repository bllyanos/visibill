from __future__ import annotations

from dataclasses import dataclass
import json
import sys
from typing import Any


TIMESTAMP_KEYS = ("timestamp", "time", "ts")
LEVEL_KEYS = ("level", "severity", "log_level")
SOURCE_KEYS = ("logger", "service", "component", "name")
MESSAGE_KEYS = ("message", "msg", "event")


@dataclass(slots=True)
class LogEvent:
    index: int
    raw_line: str
    payload: dict[str, Any] | None
    parse_error: str | None
    timestamp: str
    level: str
    source: str
    message: str
    filter_text: str


@dataclass(slots=True)
class DetailField:
    key: str
    value: str
    children: list[DetailField]


@dataclass(slots=True)
class DetailSection:
    title: str
    fields: list[DetailField]


@dataclass(slots=True)
class EventDetail:
    title: str
    summary: list[tuple[str, str]]
    sections: list[DetailSection]
    raw_json: str


def read_stdin_lines() -> list[str]:
    return [line.rstrip("\n") for line in sys.stdin]


def parse_events(lines: list[str]) -> list[LogEvent]:
    return [parse_line(index, line) for index, line in enumerate(lines, start=1)]


def parse_line(index: int, raw_line: str) -> LogEvent:
    try:
        value = json.loads(raw_line)
    except json.JSONDecodeError as exc:
        return build_fallback_event(index, raw_line, f"Invalid JSON: {exc.msg}")

    if not isinstance(value, dict):
        return build_fallback_event(
            index, raw_line, f"JSON value is {type(value).__name__}, expected object"
        )

    fields = value.get("@fields")
    nested_fields = fields if isinstance(fields, dict) else None

    timestamp = pick_display_value(value, ("@timestamp", *TIMESTAMP_KEYS))
    level = pick_display_value(value, LEVEL_KEYS, nested_fields)
    source = pick_display_value(
        value, (*SOURCE_KEYS, "methodIdentifier"), nested_fields
    )
    message = pick_display_value(value, ("@message", *MESSAGE_KEYS), nested_fields)
    if not message:
        message = summarize_payload(value)

    filter_text = " ".join(
        part for part in (message, level, source, raw_line) if part
    ).lower()
    return LogEvent(
        index=index,
        raw_line=raw_line,
        payload=value,
        parse_error=None,
        timestamp=timestamp,
        level=level,
        source=source,
        message=message,
        filter_text=filter_text,
    )


def build_fallback_event(index: int, raw_line: str, parse_error: str) -> LogEvent:
    message = raw_line or "<empty line>"
    return LogEvent(
        index=index,
        raw_line=raw_line,
        payload=None,
        parse_error=parse_error,
        timestamp="",
        level="ERROR",
        source="raw",
        message=message,
        filter_text=f"error raw {message}".lower(),
    )


def pick_display_value(
    payload: dict[str, Any],
    keys: tuple[str, ...],
    nested_payload: dict[str, Any] | None = None,
) -> str:
    for key in keys:
        if key in payload:
            return stringify_value(payload[key])
    if nested_payload is not None:
        for key in keys:
            if key in nested_payload:
                return stringify_value(nested_payload[key])
    return ""


def stringify_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def summarize_payload(payload: dict[str, Any]) -> str:
    for key, value in payload.items():
        rendered = stringify_value(value)
        if rendered:
            return f"{key}={rendered}"
    return ""


def build_event_detail(event: LogEvent) -> EventDetail:
    summary = [
        ("Index", str(event.index)),
        ("Timestamp", event.timestamp or "-"),
        ("Level", event.level or "-"),
        ("Source", event.source or "-"),
        ("Message", event.message or "-"),
    ]
    if event.parse_error:
        summary.append(("Parse error", event.parse_error))

    sections: list[DetailSection] = []
    if event.payload is not None:
        top_level_fields = [
            build_detail_field(key, value)
            for key, value in event.payload.items()
            if key != "@fields"
        ]
        if top_level_fields:
            sections.append(
                DetailSection(title="Top-level fields", fields=top_level_fields)
            )

        fields = event.payload.get("@fields")
        if isinstance(fields, dict):
            sections.append(
                DetailSection(
                    title="Nested @fields",
                    fields=[
                        build_detail_field(key, value) for key, value in fields.items()
                    ],
                )
            )
        elif fields is not None:
            sections.append(
                DetailSection(
                    title="Nested @fields",
                    fields=[build_detail_field("@fields", fields)],
                )
            )

        raw_json = json.dumps(
            event.payload, ensure_ascii=True, indent=2, sort_keys=False
        )
    else:
        raw_json = event.raw_line or "<empty line>"

    title = (
        event.message
        if event.payload is not None and event.message
        else f"Event {event.index}"
    )
    return EventDetail(
        title=title, summary=summary, sections=sections, raw_json=raw_json
    )


def build_detail_field(key: str, value: Any) -> DetailField:
    if isinstance(value, dict):
        children = [
            build_detail_field(child_key, child_value)
            for child_key, child_value in value.items()
        ]
        if children:
            return DetailField(key=key, value="", children=children)
        return DetailField(key=key, value="{}", children=[])

    if isinstance(value, list):
        children = [
            build_detail_field(f"[{index}]", child_value)
            for index, child_value in enumerate(value)
        ]
        if children:
            return DetailField(key=key, value="", children=children)
        return DetailField(key=key, value="[]", children=[])

    return DetailField(key=key, value=format_detail_value(value), children=[])


def format_detail_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value if value else '""'
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(value, ensure_ascii=True, sort_keys=True)
