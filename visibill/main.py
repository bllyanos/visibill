from __future__ import annotations

import argparse
from contextlib import contextmanager
import os
from pathlib import Path
import sys
from typing import Iterator, TextIO

from visibill.app import VisibillApp
from visibill.logs import parse_events, read_stdin_lines


@contextmanager
def interactive_stdin() -> Iterator[None]:
    original_stdin = sys.stdin
    original_dunder_stdin = sys.__stdin__
    tty_stream: TextIO | None = None

    try:
        if not original_stdin.isatty():
            tty_stream = open(os.ctermid(), encoding=original_stdin.encoding or "utf-8")
            sys.stdin = tty_stream
            sys.__stdin__ = tty_stream
        yield
    finally:
        sys.stdin = original_stdin
        sys.__stdin__ = original_dunder_stdin
        if tty_stream is not None:
            tty_stream.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="visibill",
        description="Terminal JSONL log explorer built with Textual.",
    )
    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        help="Open JSONL events from a file instead of stdin.",
    )
    return parser


def load_input_lines(file_path: Path | None) -> list[str]:
    if file_path is not None:
        return file_path.read_text(encoding="utf-8").splitlines()
    if sys.stdin.isatty():
        return []
    return read_stdin_lines()


def run(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    events = parse_events(load_input_lines(args.file))

    try:
        with interactive_stdin():
            VisibillApp(events).run()
    except OSError as exc:
        if args.file is None and not sys.stdin.isatty():
            raise SystemExit(
                f"visibill requires a controlling terminal for keyboard input when reading from a pipe: {exc}"
            ) from exc
        raise


def main() -> None:
    run()


if __name__ == "__main__":
    main()
