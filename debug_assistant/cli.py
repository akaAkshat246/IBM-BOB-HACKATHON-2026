#!/usr/bin/env python3
"""
cli.py — Command-line interface for the Debug Assistant.

Usage
-----
  # Read traceback from stdin, analyse current directory as repo
  python -m debug_assistant.cli --repo . < traceback.txt

  # Pass traceback as a file
  python -m debug_assistant.cli --repo /path/to/repo --traceback tb.txt

  # Output as HTML
  python -m debug_assistant.cli --repo . --format html --output report.html < tb.txt

  # Output as JSON
  python -m debug_assistant.cli --repo . --format json < tb.txt

  # Show step-by-step progress
  python -m debug_assistant.cli --repo . --verbose < tb.txt
"""

from __future__ import annotations

import argparse
import sys
import os

# Force UTF-8 stdout/stderr on Windows so Unicode in source comments prints cleanly
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    import io
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Allow running as `python cli.py` from the debug_assistant dir
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from debug_assistant.src import orchestrator
from debug_assistant.src.renderer import render_terminal, render_json, render_html


def _read_traceback(args: argparse.Namespace) -> str:
    if args.traceback:
        with open(args.traceback, "r", encoding="utf-8") as fh:
            return fh.read()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    # Interactive prompt
    print("Paste the traceback below, then press Ctrl-D (Unix) or Ctrl-Z+Enter (Windows):")
    return sys.stdin.read()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="debug-assistant",
        description="Trace a bug back to its root cause using full repository context.",
    )
    parser.add_argument(
        "--repo", "-r",
        default=".",
        help="Path to the repository root (default: current directory)",
    )
    parser.add_argument(
        "--traceback", "-t",
        default=None,
        help="Path to a file containing the traceback/test-failure log "
             "(default: read from stdin)",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["terminal", "json", "html"],
        default="terminal",
        help="Output format (default: terminal)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Write output to this file instead of stdout",
    )
    parser.add_argument(
        "--depth", "-d",
        type=int,
        default=10,
        help="Maximum frames to trace backward (default: 10)",
    )
    parser.add_argument(
        "--no-colour",
        action="store_true",
        help="Disable ANSI colour codes in terminal output",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print progress to stderr while running",
    )

    args = parser.parse_args()

    repo_root = os.path.abspath(args.repo)
    if not os.path.isdir(repo_root):
        print(f"Error: --repo '{repo_root}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    traceback_text = _read_traceback(args)
    if not traceback_text.strip():
        print("Error: no traceback provided.", file=sys.stderr)
        sys.exit(1)

    # Progress goes to stderr so it doesn't pollute piped output
    if args.verbose:
        import debug_assistant.src.orchestrator as _orch
        # Monkey-patch verbose=True into the run call
        report = _orch.run(
            traceback_text=traceback_text,
            repo_root=repo_root,
            max_trace_depth=args.depth,
            verbose=True,
        )
    else:
        report = orchestrator.run(
            traceback_text=traceback_text,
            repo_root=repo_root,
            max_trace_depth=args.depth,
            verbose=False,
        )

    # Render
    if args.format == "terminal":
        output = render_terminal(report, no_colour=args.no_colour)
    elif args.format == "json":
        output = render_json(report)
    else:  # html
        output = render_html(report)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(output)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
