"""ai-eval-forge: zero-dependency eval harness for LLM and agent regression testing.

Python port of @mukundakatta/ai-eval-forge on npm. Same check types and output
shape, so cases.jsonl written for the npm version work here unchanged.
"""

from ai_eval_forge.evaluator import (
    CaseResult,
    CheckResult,
    SuiteResult,
    Summary,
    evaluate_case,
    evaluate_suite,
    parse_cases,
    run_check,
    token_f1,
)
from ai_eval_forge.reporter import render_markdown

__all__ = [
    "CaseResult",
    "CheckResult",
    "SuiteResult",
    "Summary",
    "evaluate_case",
    "evaluate_suite",
    "parse_cases",
    "run_check",
    "token_f1",
    "render_markdown",
]

__version__ = "0.1.0"
