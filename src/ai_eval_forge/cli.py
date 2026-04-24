"""Command-line entry point for ai-eval-forge."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from ai_eval_forge import __version__
from ai_eval_forge.compare import compare_files, render_compare_markdown
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

    # `aef score`
    score = sub.add_parser("score", help="Score a cases file (JSON array or JSONL).")
    score.add_argument("file", help="Path to the cases file (JSON array or JSONL).")
    score.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format (default: json).",
    )

    # `aef compare`
    compare = sub.add_parser(
        "compare",
        help="Compare two suite-result JSON files (from `aef score`) and report regressions.",
    )
    compare.add_argument("baseline", help="Baseline suite-result JSON (previous / known-good run).")
    compare.add_argument("current", help="Current suite-result JSON (new run to check).")
    compare.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="markdown",
        help="Output format (default: markdown).",
    )
    compare.add_argument(
        "--baseline-label",
        default="baseline",
        help="Display label for the baseline (default: 'baseline').",
    )
    compare.add_argument(
        "--current-label",
        default="current",
        help="Display label for the current run (default: 'current').",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"ai-eval-forge {__version__}",
    )
    args = parser.parse_args(argv)

    if args.command == "score":
        return _run_score(args)
    if args.command == "compare":
        return _run_compare(args)
    return 2


def _run_score(args: argparse.Namespace) -> int:
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


def _run_compare(args: argparse.Namespace) -> int:
    baseline_path = Path(args.baseline)
    current_path = Path(args.current)
    for p in (baseline_path, current_path):
        if not p.exists():
            print(f"error: file not found: {p}", file=sys.stderr)
            return 2

    try:
        diff = compare_files(str(baseline_path), str(current_path))
    except json.JSONDecodeError as exc:
        print(f"error: failed to parse suite-result JSON: {exc}", file=sys.stderr)
        return 2

    if args.format == "markdown":
        sys.stdout.write(
            render_compare_markdown(
                diff,
                baseline_label=args.baseline_label,
                current_label=args.current_label,
            )
        )
    else:
        sys.stdout.write(json.dumps(diff.to_dict(), indent=2) + "\n")

    return 1 if diff.has_regressions else 0


if __name__ == "__main__":
    raise SystemExit(main())
