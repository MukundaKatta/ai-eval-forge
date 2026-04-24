"""Markdown report renderer."""

from __future__ import annotations

from ai_eval_forge.evaluator import SuiteResult


def _escape_table_cell(value: str) -> str:
    return str(value).replace("|", "\\|")


def render_markdown(result: SuiteResult) -> str:
    summary = result.summary
    lines = [
        "# AI Eval Forge Report",
        "",
        f"- Total: {summary.total}",
        f"- Passed: {summary.passed}",
        f"- Failed: {summary.failed}",
        f"- Pass rate: {round(summary.passRate * 100)}%",
        f"- Average score: {round(summary.averageScore, 4)}",
        "",
        "| Case | Result | Score | Failed checks |",
        "| --- | --- | ---: | --- |",
    ]
    for case in result.cases:
        failed_types = ", ".join(c.type for c in case.checks if not c.passed)
        lines.append(
            f"| {_escape_table_cell(case.id)} | "
            f"{'pass' if case.passed else 'fail'} | "
            f"{case.score} | "
            f"{_escape_table_cell(failed_types or '-')} |"
        )
    return "\n".join(lines) + "\n"
