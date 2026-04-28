from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

from visibill.logs import LogEvent


OPERATORS: Final[tuple[str, ...]] = ("!=", ">=", "<=", "=", "~", ">", "<")
OPERATOR_CHARS: Final[frozenset[str]] = frozenset("!=~<>")
SUPPORTED_FIELDS: Final[frozenset[str]] = frozenset(
    {"timestamp", "level", "source", "message", "raw"}
)
FIELD_ALIASES: Final[dict[str, str]] = {
    "ts": "timestamp",
    "logger": "source",
    "method": "source",
}


class FilterParseError(ValueError):
    """Raised when a structured filter cannot be parsed."""


@dataclass(slots=True)
class FilterClause:
    field: str
    operator: str
    value: str


@dataclass(slots=True)
class FilterQuery:
    raw: str
    text_fallback: str | None
    clauses: list[FilterClause]


def has_structured_operator(raw: str) -> bool:
    return any(operator in raw for operator in OPERATORS)


def parse_filter(raw: str) -> FilterQuery:
    stripped = raw.strip()
    if not stripped:
        return FilterQuery(raw=raw, text_fallback=None, clauses=[])

    if not has_structured_operator(stripped):
        return FilterQuery(raw=raw, text_fallback=stripped.lower(), clauses=[])

    clauses = [parse_clause(token) for token in stripped.split()]
    return FilterQuery(raw=raw, text_fallback=None, clauses=clauses)


def parse_clause(token: str) -> FilterClause:
    for operator in OPERATORS:
        field_name, separator, value = token.partition(operator)
        if not separator:
            continue

        if not field_name:
            raise FilterParseError(f"invalid clause {token!r}")

        if not value:
            raise FilterParseError(f"missing value for field '{field_name}'")

        if value[0] in OPERATOR_CHARS:
            raise FilterParseError(f"invalid clause {token!r}")

        field = normalize_field(field_name)
        if operator in {">", ">=", "<", "<="} and field != "timestamp":
            raise FilterParseError(
                f"comparison operator '{operator}' is only supported for 'timestamp'"
            )

        return FilterClause(field=field, operator=operator, value=strip_quotes(value))

    raise FilterParseError(f"invalid clause {token!r}")


def normalize_field(field_name: str) -> str:
    field = FIELD_ALIASES.get(field_name.lower(), field_name.lower())
    if field not in SUPPORTED_FIELDS:
        raise FilterParseError(f"unknown field '{field_name}'")
    return field


def strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def matches_filter(event: LogEvent, query: FilterQuery) -> bool:
    if query.text_fallback is not None:
        return query.text_fallback in event.filter_text
    return all(matches_clause(event, clause) for clause in query.clauses)


def matches_clause(event: LogEvent, clause: FilterClause) -> bool:
    value = get_field_value(event, clause.field)
    if clause.field == "timestamp":
        return matches_timestamp_clause(value, clause.operator, clause.value)
    return matches_string_clause(value, clause.operator, clause.value)


def get_field_value(event: LogEvent, field: str) -> str:
    if field == "timestamp":
        return event.timestamp
    if field == "level":
        return event.level
    if field == "source":
        return event.source
    if field == "message":
        return event.message
    if field == "raw":
        return event.raw_line
    raise AssertionError(f"unsupported field {field!r}")


def matches_string_clause(actual: str, operator: str, expected: str) -> bool:
    actual_normalized = actual.lower()
    expected_normalized = expected.lower()

    if operator == "=":
        return actual_normalized == expected_normalized
    if operator == "!=":
        return actual_normalized != expected_normalized
    if operator == "~":
        return expected_normalized in actual_normalized
    raise AssertionError(f"unsupported string operator {operator!r}")


def matches_timestamp_clause(actual: str, operator: str, expected: str) -> bool:
    if not actual:
        return False

    actual_normalized = normalize_timestamp(actual)
    expected_normalized = normalize_timestamp(expected)

    if operator == "=":
        return actual_normalized == expected_normalized
    if operator == "!=":
        return actual_normalized != expected_normalized
    if operator == "~":
        return expected_normalized in actual_normalized
    if operator == ">":
        return actual_normalized > expected_normalized
    if operator == ">=":
        return actual_normalized >= expected_normalized
    if operator == "<":
        return actual_normalized < expected_normalized
    if operator == "<=":
        return actual_normalized <= expected_normalized
    raise AssertionError(f"unsupported timestamp operator {operator!r}")


def normalize_timestamp(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        return normalized

    parsed = parse_iso_timestamp(normalized)
    if parsed is not None:
        return parsed.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    if normalized.endswith("z"):
        return f"{normalized[:-1]}Z"
    return normalized


def parse_iso_timestamp(value: str) -> datetime | None:
    candidate = value
    if candidate.endswith("Z") or candidate.endswith("z"):
        candidate = f"{candidate[:-1]}+00:00"

    # Keep date-only values as prefixes so comparisons like timestamp>='2026-04-13'
    # continue to behave as date-prefix filters in the first pass.
    if "T" not in candidate and " " not in candidate:
        return None

    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        return None
