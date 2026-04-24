"""Core evaluator: checks, cases, suites.

This is a line-for-line Python port of the npm @mukundakatta/ai-eval-forge
src/index.js v0.1.0, with one deliberate change: the `js_expression` check
type is dropped from this release because Python's equivalent (``eval``) is
harder to sandbox safely. Files written for the npm version with other
check types work here unchanged.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

DEFAULT_CHECKS: list[dict] = [{"type": "token_f1", "min": 0.65}]


# ---------- Dataclasses ----------


@dataclass
class CheckResult:
    type: str
    required: bool
    passed: bool
    score: float
    min: float
    detail: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CaseMeta:
    input: Any = None
    tags: list = field(default_factory=list)
    costUsd: float = 0.0
    latencyMs: float = 0.0


@dataclass
class CaseResult:
    id: str
    passed: bool
    score: float
    checks: list[CheckResult]
    meta: dict

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "passed": self.passed,
            "score": self.score,
            "checks": [c.to_dict() for c in self.checks],
            "meta": self.meta,
        }


@dataclass
class Summary:
    total: int
    passed: int
    failed: int
    passRate: float
    averageScore: float
    totalCostUsd: float
    averageLatencyMs: int


@dataclass
class SuiteResult:
    summary: Summary
    cases: list[CaseResult]

    def to_dict(self) -> dict:
        return {
            "summary": asdict(self.summary),
            "cases": [c.to_dict() for c in self.cases],
        }


# ---------- Helpers ----------


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def _normalize(value: Any) -> str:
    return re.sub(r"\s+", " ", _stringify(value).lower()).strip()


def _tokenize(value: Any) -> list[str]:
    return re.findall(r"[a-z0-9]+", _normalize(value))


def _arrayify(value: Any) -> list:
    return list(value) if isinstance(value, list) else [value]


def _round(value: float, places: int = 4) -> float:
    factor = 10 ** places
    return round(value * factor) / factor


def _parse_json(value: str) -> tuple[bool, Any]:
    try:
        return True, json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return False, None


def _get_path(value: Any, dotted: str) -> Any:
    current = value
    for key in [k for k in str(dotted or "").split(".") if k]:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list):
            try:
                current = current[int(key)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return current


def _deep_equal(left: Any, right: Any) -> bool:
    return json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)


def token_f1(actual: Any, expected: Any) -> float:
    """F1 over lowercase alphanumeric tokens."""
    actual_tokens = _tokenize(actual)
    expected_tokens = _tokenize(expected)
    if not actual_tokens and not expected_tokens:
        return 1.0
    if not actual_tokens or not expected_tokens:
        return 0.0

    expected_counts: dict[str, int] = {}
    for t in expected_tokens:
        expected_counts[t] = expected_counts.get(t, 0) + 1

    overlap = 0
    for t in actual_tokens:
        if expected_counts.get(t, 0) > 0:
            overlap += 1
            expected_counts[t] -= 1

    precision = overlap / len(actual_tokens)
    recall = overlap / len(expected_tokens)
    denom = precision + recall
    if denom == 0:
        return 0.0
    return (2 * precision * recall) / denom


def citation_coverage(actual: str, sources: list) -> float:
    """Fraction of source IDs that appear (in [id], (id), or raw form) inside actual."""
    ids = [str(s.get("id", s) if isinstance(s, dict) else s) for s in sources]
    ids = [i for i in ids if i]
    if not ids:
        return 1.0
    cited = [i for i in ids if f"[{i}]" in actual or f"({i})" in actual or i in actual]
    return len(cited) / len(ids)


# ---------- Checks ----------


def run_check(check: dict, context: dict) -> CheckResult:
    required = check.get("required") is not False
    check_type = check.get("type") or "token_f1"
    min_score = float(check.get("min", 1))
    actual = context["actual"]
    expected = context["expected"]
    test_case = context.get("testCase", {})

    score: float = 0.0
    detail: str = ""

    if check_type == "exact":
        target = check.get("value", expected)
        score = 1.0 if _normalize(actual) == _normalize(target) else 0.0

    elif check_type == "contains":
        values = [str(v) for v in _arrayify(check.get("value", expected))]
        case_sensitive = bool(check.get("caseSensitive"))
        haystack = actual if case_sensitive else actual.lower()
        hits = [
            v
            for v in values
            if (v if case_sensitive else v.lower()) in haystack
        ]
        score = len(hits) / len(values) if values else 1.0
        detail = f"{len(hits)}/{len(values)} substrings found"

    elif check_type == "regex":
        pattern = check.get("pattern") or check.get("value")
        flags_str = check.get("flags", "i")
        flags = 0
        if "i" in flags_str:
            flags |= re.IGNORECASE
        if "m" in flags_str:
            flags |= re.MULTILINE
        if "s" in flags_str:
            flags |= re.DOTALL
        score = 1.0 if re.search(pattern, actual, flags) else 0.0

    elif check_type == "token_f1":
        target = check.get("value", expected)
        score = token_f1(actual, target)
        detail = f"token_f1={_round(score, 4)}"

    elif check_type == "json_valid":
        ok, _ = _parse_json(actual)
        score = 1.0 if ok else 0.0

    elif check_type == "json_field":
        ok, parsed = _parse_json(actual)
        actual_value = _get_path(parsed, check.get("path")) if ok else None
        score = 1.0 if _deep_equal(actual_value, check.get("value")) else 0.0
        detail = f"{check.get('path')}={json.dumps(actual_value)}"

    elif check_type == "citation_coverage":
        sources = check.get("sources") or test_case.get("sources") or []
        score = citation_coverage(actual, sources)
        detail = f"citation_coverage={_round(score, 4)}"

    else:
        raise ValueError(f"Unknown check type: {check_type}")

    return CheckResult(
        type=check_type,
        required=required,
        passed=score >= min_score,
        score=_round(score, 4),
        min=min_score,
        detail=detail,
    )


# ---------- Case + suite evaluation ----------


def evaluate_case(test_case: dict, index: int = 0) -> CaseResult:
    checks = test_case.get("checks") or DEFAULT_CHECKS
    actual = _stringify(test_case.get("actual", test_case.get("output", "")))
    expected = _stringify(test_case.get("expected", test_case.get("reference", "")))
    context = {"actual": actual, "expected": expected, "testCase": test_case}

    check_results = [run_check(c, context) for c in checks]
    required_results = [r for r in check_results if r.required]
    pass_set = required_results if required_results else check_results
    passed = all(r.passed for r in pass_set)
    score = (
        sum(r.score for r in check_results) / len(check_results)
        if check_results
        else 1.0
    )

    meta = {
        "input": test_case.get("input"),
        "tags": test_case.get("tags") or [],
        "costUsd": float(test_case.get("costUsd", (test_case.get("meta") or {}).get("costUsd", 0))),
        "latencyMs": float(test_case.get("latencyMs", (test_case.get("meta") or {}).get("latencyMs", 0))),
    }

    return CaseResult(
        id=test_case.get("id") or f"case-{index}",
        passed=passed,
        score=_round(score, 4),
        checks=check_results,
        meta=meta,
    )


def evaluate_suite(cases: Iterable[dict]) -> SuiteResult:
    evaluated = [evaluate_case(c, idx) for idx, c in enumerate(cases)]
    total = len(evaluated)
    passed = sum(1 for c in evaluated if c.passed)
    failed = total - passed
    score_sum = sum(c.score for c in evaluated)
    cost_sum = sum(float(c.meta.get("costUsd") or 0) for c in evaluated)
    latency_sum = sum(float(c.meta.get("latencyMs") or 0) for c in evaluated)

    summary = Summary(
        total=total,
        passed=passed,
        failed=failed,
        passRate=(passed / total) if total else 0.0,
        averageScore=(score_sum / total) if total else 0.0,
        totalCostUsd=_round(cost_sum, 6),
        averageLatencyMs=round(latency_sum / total) if total else 0,
    )
    return SuiteResult(summary=summary, cases=evaluated)


def parse_cases(text: str) -> list[dict]:
    """Accepts either a JSON array or JSONL (one object per line)."""
    trimmed = text.strip()
    if not trimmed:
        return []
    if trimmed.startswith("["):
        return json.loads(trimmed)
    return [json.loads(line) for line in trimmed.split("\n") if line.strip()]
