from __future__ import annotations

from io import StringIO
from pathlib import Path
import unittest
from unittest.mock import patch

from visibill import main


class BuildParserTests(unittest.TestCase):
    def test_help_mentions_file_option(self) -> None:
        parser = main.build_parser()

        with self.assertRaises(SystemExit) as exc:
            parser.parse_args(["--help"])

        self.assertEqual(exc.exception.code, 0)


class LoadInputLinesTests(unittest.TestCase):
    def test_reads_lines_from_file_argument(self) -> None:
        sample_path = Path(__file__).resolve().parents[1] / "sample.log"

        lines = main.load_input_lines(sample_path)

        self.assertGreater(len(lines), 0)
        self.assertIn('"@timestamp"', lines[0])

    def test_reads_lines_from_piped_stdin_when_no_file_given(self) -> None:
        fake_stdin = StringIO("first\nsecond\n")
        fake_stdin.isatty = lambda: False  # type: ignore[method-assign]

        with patch.object(main.sys, "stdin", fake_stdin):
            lines = main.load_input_lines(None)

        self.assertEqual(lines, ["first", "second"])

    def test_uses_empty_input_for_interactive_session_without_file(self) -> None:
        fake_stdin = StringIO("")
        fake_stdin.isatty = lambda: True  # type: ignore[method-assign]

        with patch.object(main.sys, "stdin", fake_stdin):
            lines = main.load_input_lines(None)

        self.assertEqual(lines, [])


class RunTests(unittest.TestCase):
    def test_help_exits_cleanly(self) -> None:
        stderr = StringIO()
        stdout = StringIO()

        with patch("sys.stdout", stdout), patch("sys.stderr", stderr):
            with self.assertRaises(SystemExit) as exc:
                main.run(["--help"])

        self.assertEqual(exc.exception.code, 0)
        self.assertIn("usage: visibill", stdout.getvalue())
        self.assertIn("-f", stdout.getvalue())

    def test_file_argument_loads_events_and_runs_app(self) -> None:
        sample_path = Path(__file__).resolve().parents[1] / "sample.log"

        with patch.object(main, "interactive_stdin") as interactive_stdin:
            interactive_stdin.return_value.__enter__.return_value = None
            interactive_stdin.return_value.__exit__.return_value = None

            with patch.object(main.VisibillApp, "run", autospec=True) as run_app:
                main.run(["--file", str(sample_path)])

        run_app.assert_called_once()
        app = run_app.call_args.args[0]
        self.assertGreater(len(app.all_events), 0)

    def test_missing_file_surfaces_os_error(self) -> None:
        missing = Path("/tmp/visibill-missing-file.log")

        with self.assertRaises(FileNotFoundError):
            main.run(["--file", str(missing)])


if __name__ == "__main__":
    unittest.main()
