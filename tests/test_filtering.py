from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import Mock

from visibill.app import FILTER_DEBOUNCE_SECONDS, DetailScreen, VisibillApp
from visibill.filtering import FilterParseError, matches_filter, parse_filter
from visibill.logs import build_event_detail, parse_events


def load_sample_events() -> list:
    sample_path = Path(__file__).resolve().parents[1] / "sample.log"
    return parse_events(sample_path.read_text(encoding="utf-8").splitlines())


class ParseFilterTests(unittest.TestCase):
    def test_parses_single_equality_clause(self) -> None:
        query = parse_filter("level=error")

        self.assertIsNone(query.text_fallback)
        self.assertEqual(len(query.clauses), 1)
        self.assertEqual(query.clauses[0].field, "level")
        self.assertEqual(query.clauses[0].operator, "=")
        self.assertEqual(query.clauses[0].value, "error")

    def test_parses_contains_clause(self) -> None:
        query = parse_filter("message~upload")

        self.assertEqual(query.clauses[0].field, "message")
        self.assertEqual(query.clauses[0].operator, "~")
        self.assertEqual(query.clauses[0].value, "upload")

    def test_parses_quoted_timestamp_comparison(self) -> None:
        query = parse_filter("timestamp>='2026-04-13'")

        self.assertEqual(query.clauses[0].field, "timestamp")
        self.assertEqual(query.clauses[0].operator, ">=")
        self.assertEqual(query.clauses[0].value, "2026-04-13")

    def test_parses_multiple_clauses(self) -> None:
        query = parse_filter("level=info source~aws")

        self.assertEqual(len(query.clauses), 2)
        self.assertEqual(query.clauses[0].field, "level")
        self.assertEqual(query.clauses[1].field, "source")

    def test_parses_quoted_value_with_spaces(self) -> None:
        query = parse_filter('message~"document expiration"')

        self.assertEqual(len(query.clauses), 1)
        self.assertEqual(query.clauses[0].field, "message")
        self.assertEqual(query.clauses[0].operator, "~")
        self.assertEqual(query.clauses[0].value, "document expiration")

    def test_parses_multiple_clauses_with_quoted_value(self) -> None:
        query = parse_filter('level=info message~"document expiration"')

        self.assertEqual(len(query.clauses), 2)
        self.assertEqual(query.clauses[0].field, "level")
        self.assertEqual(query.clauses[1].field, "message")
        self.assertEqual(query.clauses[1].value, "document expiration")

    def test_rejects_double_equals(self) -> None:
        with self.assertRaisesRegex(FilterParseError, r"invalid clause"):
            parse_filter("level==error")

    def test_rejects_unknown_field(self) -> None:
        with self.assertRaisesRegex(FilterParseError, r"unknown field 'unknown'"):
            parse_filter("unknown=foo")

    def test_rejects_unterminated_quote(self) -> None:
        with self.assertRaisesRegex(FilterParseError, r"No closing quotation"):
            parse_filter('message~"document expiration')


class MatchFilterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.events = load_sample_events()

    def assert_matching_indexes(
        self, filter_text: str, expected_indexes: list[int]
    ) -> None:
        query = parse_filter(filter_text)
        matches = [event.index for event in self.events if matches_filter(event, query)]
        self.assertEqual(matches, expected_indexes)

    def test_level_equality(self) -> None:
        self.assert_matching_indexes("level=info", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

    def test_source_contains(self) -> None:
        self.assert_matching_indexes("source~AwsS3Client", [6, 7])

    def test_message_contains(self) -> None:
        self.assert_matching_indexes("message~expiration", [9, 10])

    def test_message_contains_with_quoted_spaces(self) -> None:
        self.assert_matching_indexes('message~"document expiration"', [9, 10])

    def test_timestamp_greater_equal(self) -> None:
        self.assert_matching_indexes("timestamp>='2026-04-28T10:40:00Z'", [9, 10])

    def test_multiple_clauses_are_implicit_and(self) -> None:
        self.assert_matching_indexes("level=info source~AwsS3Client", [6, 7])


class EventDetailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.events = load_sample_events()

    def test_builds_structured_detail_for_nested_fields(self) -> None:
        detail = build_event_detail(self.events[0])

        self.assertEqual(
            detail.title,
            "[Loggable] PerCabinetDocumentTempFileGenerator.flushToTempFile - s",
        )
        self.assertEqual(detail.summary[0], ("Index", "1"))
        self.assertEqual(detail.summary[1], ("Timestamp", "2026-04-28T10:39:54.128Z"))
        self.assertEqual(
            [section.title for section in detail.sections],
            ["Top-level fields", "Nested @fields"],
        )
        nested_fields = detail.sections[1].fields
        self.assertEqual(nested_fields[0].key, "0")
        self.assertEqual(
            nested_fields[0].value, "/9998118-MDMyNmEwMGM/REVIEW/15_9998118_000.jpg.txt"
        )
        self.assertEqual(nested_fields[4].key, "memoryUsage")
        self.assertGreater(len(nested_fields[4].children), 0)

    def test_builds_fallback_detail_for_parse_errors(self) -> None:
        detail = build_event_detail(parse_events(["not json"])[0])

        self.assertEqual(detail.title, "Event 1")
        self.assertEqual(detail.sections, [])
        self.assertIn("Invalid JSON", detail.summary[-1][1])


class OpenDetailActionTests(unittest.TestCase):
    def test_open_detail_uses_cursor_row(self) -> None:
        class CaptureApp(VisibillApp):
            def __init__(self) -> None:
                super().__init__(load_sample_events())
                self.opened = None

            def push_screen(self, screen: DetailScreen) -> None:  # type: ignore[override]
                self.opened = screen

        app = CaptureApp()
        app.visible_events = app.all_events[:2]
        app.open_detail_for_index(1)

        self.assertIsInstance(app.opened, DetailScreen)
        self.assertEqual(app.opened.detail.summary[0], ("Index", "2"))

    def test_row_selected_handler_uses_cursor_row(self) -> None:
        class CaptureApp(VisibillApp):
            def __init__(self) -> None:
                super().__init__(load_sample_events())
                self.selected_index = None

            def open_detail_for_index(self, index: int) -> None:
                self.selected_index = index

        class RowSelectedEvent:
            def __init__(self, cursor_row: int) -> None:
                self.cursor_row = cursor_row

        app = CaptureApp()
        app.handle_row_selected(RowSelectedEvent(3))

        self.assertEqual(app.selected_index, 3)


class FilterDebounceTests(unittest.TestCase):
    def test_filter_change_schedules_debounced_apply(self) -> None:
        class ChangedEvent:
            def __init__(self, value: str) -> None:
                self.value = value

        app = VisibillApp(load_sample_events())
        timer = Mock()
        app.set_timer = Mock(return_value=timer)  # type: ignore[method-assign]

        app.handle_filter_changed(ChangedEvent("level=info"))

        app.set_timer.assert_called_once()
        self.assertEqual(app.set_timer.call_args.args[0], FILTER_DEBOUNCE_SECONDS)
        self.assertTrue(callable(app.set_timer.call_args.args[1]))
        self.assertEqual(app.pending_filter_value, "level=info")
        self.assertIs(app.filter_debounce_timer, timer)

    def test_filter_change_replaces_pending_timer(self) -> None:
        class ChangedEvent:
            def __init__(self, value: str) -> None:
                self.value = value

        app = VisibillApp(load_sample_events())
        first_timer = Mock()
        second_timer = Mock()
        app.set_timer = Mock(side_effect=[first_timer, second_timer])  # type: ignore[method-assign]

        app.handle_filter_changed(ChangedEvent("level=i"))
        app.handle_filter_changed(ChangedEvent("level=info"))

        first_timer.stop.assert_called_once_with()
        self.assertEqual(app.pending_filter_value, "level=info")
        self.assertIs(app.filter_debounce_timer, second_timer)

    def test_stale_timer_callback_is_ignored(self) -> None:
        class ChangedEvent:
            def __init__(self, value: str) -> None:
                self.value = value

        app = VisibillApp(load_sample_events())
        first_timer = Mock()
        second_timer = Mock()
        app.set_timer = Mock(side_effect=[first_timer, second_timer])  # type: ignore[method-assign]
        app.apply_filter = Mock()  # type: ignore[method-assign]

        app.handle_filter_changed(ChangedEvent("level=i"))
        first_callback = app.set_timer.call_args_list[0].args[1]
        app.handle_filter_changed(ChangedEvent("level=info"))

        first_callback()

        app.apply_filter.assert_not_called()

    def test_apply_pending_filter_uses_latest_typed_value(self) -> None:
        app = VisibillApp(load_sample_events())
        app.pending_filter_value = "message~expiration"
        app.refresh_table = Mock()  # type: ignore[method-assign]

        app.apply_pending_filter()

        self.assertIsNone(app.filter_debounce_timer)
        self.assertEqual([event.index for event in app.visible_events], [9, 10])


if __name__ == "__main__":
    unittest.main()
