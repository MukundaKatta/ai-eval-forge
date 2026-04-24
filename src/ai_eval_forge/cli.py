"""Command-line entry point for ai-eval-forge."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from ai_eval_forge import __version__
from ai_eval_forge.evaluator import evaluate_suite, parse_cases
from ai_eval_forge.reporter import render_markdown


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ai-eval-forge",
        description=(
            "Zero-dependency eval harness for LLM and agent regression testing. "
            "Scores outputs with exact, contains, regex, JSON, citation, and "
            "token-F1 checks."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    score = sub.add_parser("score", help="Score a cases file (JSON array or JSONL).")
    score.add_argument("file", help="Path to the cases file (JSON array or JSONL).")
    score.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format (default: json).",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"ai-eval-forge {__version__}",
    )
    args = parser.parse_args(argv)

    if args.command == "score":
        path = Path(args.file)
        if not path.exists():
            print(f"error: file not found: {path}", file=sys.stderr)
            return 2
        text = path.read_text(encoding="utf-8")
        cases = parse_cases(text)
        result = evaluate_suite(cases)

        if args.format == "markdown":
            sys.stdout.write(render_markdown(result))
        else:
            sys.stdout.write(json.dumps(result.to_dict(), indent=2) + "\n")

        return 1 if result.summary.failed else 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
