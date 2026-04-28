from __future__ import annotations

from contextlib import contextmanager
import os
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


def main() -> None:
    lines = [] if sys.stdin.isatty() else read_stdin_lines()
    events = parse_events(lines)

    try:
        with interactive_stdin():
            VisibillApp(events).run()
    except OSError as exc:
        if not sys.stdin.isatty():
            raise SystemExit(
                f"visibill requires a controlling terminal for keyboard input when reading from a pipe: {exc}"
            ) from exc
        raise


if __name__ == "__main__":
    main()
