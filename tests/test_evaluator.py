"""Tests for the evaluator — ported 1:1 from the npm package behavior."""

from __future__ import annotations

import json

import pytest

from ai_eval_forge.evaluator import (
    evaluate_case,
    evaluate_suite,
    parse_cases,
    run_check,
    token_f1,
)


# ---------- token_f1 ----------


def test_token_f1_perfect_match() -> None:
    assert token_f1("hello world", "hello world") == 1.0


def test_token_f1_no_overlap() -> None:
    assert token_f1("alpha beta", "gamma delta") == 0.0


def test_token_f1_partial() -> None:
    # "the cat sat" vs "the cat" → overlap 2, precision 2/3, recall 2/2, F1 = 0.8
    score = token_f1("the cat sat", "the cat")
    assert 0.79 < score < 0.81


def test_token_f1_case_insensitive() -> None:
    assert token_f1("HELLO", "hello") == 1.0


def test_token_f1_both_empty() -> None:
    assert token_f1("", "") == 1.0


def test_token_f1_one_empty() -> None:
    assert token_f1("", "hello") == 0.0


# ---------- run_check: individual types ----------


def _ctx(actual: str, expected: str = "", test_case: dict | None = None) -> dict:
    return {"actual": actual, "expected": expected, "testCase": test_case or {}}


def test_exact_match_passes() -> None:
    r = run_check({"type": "exact", "value": "Hello"}, _ctx("hello"))
    assert r.passed
    assert r.score == 1.0


def test_exact_mismatch_fails() -> None:
    r = run_check({"type": "exact", "value": "Hello"}, _ctx("world"))
    assert not r.passed


def test_contains_single() -> None:
    r = run_check({"type": "contains", "value": "forge"}, _ctx("AI Eval Forge"))
    assert r.passed


def test_contains_multi_all_present() -> None:
    r = run_check(
        {"type": "contains", "value": ["alpha", "beta"]},
        _ctx("alpha and beta here"),
    )
    assert r.score == 1.0


def test_contains_multi_partial_fails_default_min() -> None:
    # Default min is 1.0; half-matching scores 0.5 and should fail.
    r = run_check(
        {"type": "contains", "value": ["alpha", "beta"]},
        _ctx("only alpha"),
    )
    assert r.score == 0.5
    assert not r.passed


def test_contains_min_threshold() -> None:
    r = run_check(
        {"type": "contains", "value": ["alpha", "beta"], "min": 0.5},
        _ctx("only alpha"),
    )
    assert r.passed


def test_regex_passes() -> None:
    r = run_check({"type": "regex", "pattern": r"\d{4}"}, _ctx("code 1234 here"))
    assert r.passed


def test_regex_fails() -> None:
    r = run_check({"type": "regex", "pattern": r"\d{4}"}, _ctx("no digits"))
    assert not r.passed


def test_token_f1_via_run_check() -> None:
    r = run_check({"type": "token_f1"}, _ctx("the quick fox", "the quick brown fox"))
    assert r.score > 0.8


def test_json_valid_true() -> None:
    r = run_check({"type": "json_valid"}, _ctx('{"a":1}'))
    assert r.passed


def test_json_valid_false() -> None:
    r = run_check({"type": "json_valid"}, _ctx("not json"))
    assert not r.passed


def test_json_field_match() -> None:
    r = run_check(
        {"type": "json_field", "path": "user.name", "value": "Alice"},
        _ctx('{"user":{"name":"Alice"}}'),
    )
    assert r.passed


def test_json_field_nested_mismatch() -> None:
    r = run_check(
        {"type": "json_field", "path": "user.name", "value": "Bob"},
        _ctx('{"user":{"name":"Alice"}}'),
    )
    assert not r.passed


def test_citation_coverage_all_cited() -> None:
    sources = [{"id": "src1"}, {"id": "src2"}]
    r = run_check(
        {"type": "citation_coverage"},
        _ctx("See [src1] and [src2].", test_case={"sources": sources}),
    )
    assert r.score == 1.0


def test_citation_coverage_partial() -> None:
    sources = [{"id": "src1"}, {"id": "src2"}, {"id": "src3"}]
    r = run_check(
        {"type": "citation_coverage", "min": 0.5},
        _ctx("See [src1] and [src2].", test_case={"sources": sources}),
    )
    # 2/3 cited; score is rounded to 4 decimals by run_check
    assert abs(r.score - 0.6667) < 1e-4
    assert r.passed


def test_citation_coverage_empty_sources_trivially_passes() -> None:
    r = run_check(
        {"type": "citation_coverage"},
        _ctx("anything", test_case={"sources": []}),
    )
    assert r.score == 1.0


def test_unknown_check_raises() -> None:
    with pytest.raises(ValueError):
        run_check({"type": "made_up"}, _ctx("x"))


# ---------- evaluate_case / evaluate_suite ----------


def test_evaluate_case_default_check_is_token_f1() -> None:
    case = {"actual": "the quick brown fox", "expected": "the quick brown fox"}
    res = evaluate_case(case)
    assert res.passed
    assert res.score == 1.0


def test_evaluate_case_default_id_when_missing() -> None:
    case = {"actual": "hi", "expected": "hi"}
    res = evaluate_case(case, index=7)
    assert res.id == "case-7"


def test_evaluate_case_uses_custom_id() -> None:
    case = {"id": "custom", "actual": "x", "expected": "x"}
    assert evaluate_case(case).id == "custom"


def test_evaluate_case_required_controls_pass() -> None:
    case = {
        "actual": "hello",
        "expected": "world",
        "checks": [
            {"type": "exact", "value": "hello", "required": False},
            {"type": "exact", "value": "hello"},  # required (default)
        ],
    }
    res = evaluate_case(case)
    assert res.passed  # required check passed


def test_evaluate_case_meta_captured() -> None:
    case = {
        "actual": "x",
        "expected": "x",
        "tags": ["regression"],
        "costUsd": 0.05,
        "latencyMs": 123,
    }
    res = evaluate_case(case)
    assert res.meta["tags"] == ["regression"]
    assert res.meta["costUsd"] == 0.05


def test_evaluate_suite_summary() -> None:
    cases = [
        {"actual": "hello", "expected": "hello"},
        {"actual": "world", "expected": "xyz"},
    ]
    suite = evaluate_suite(cases)
    assert suite.summary.total == 2
    assert suite.summary.passed == 1
    assert suite.summary.failed == 1
    assert suite.summary.passRate == 0.5


def test_evaluate_suite_empty() -> None:
    suite = evaluate_suite([])
    assert suite.summary.total == 0
    assert suite.summary.passRate == 0.0


def test_evaluate_suite_sums_cost_and_latency() -> None:
    cases = [
        {"actual": "a", "expected": "a", "costUsd": 0.1, "latencyMs": 100},
        {"actual": "b", "expected": "b", "costUsd": 0.2, "latencyMs": 300},
    ]
    suite = evaluate_suite(cases)
    assert abs(suite.summary.totalCostUsd - 0.3) < 1e-9
    assert suite.summary.averageLatencyMs == 200


# ---------- parse_cases ----------


def test_parse_cases_json_array() -> None:
    text = json.dumps([{"actual": "a", "expected": "a"}, {"actual": "b", "expected": "b"}])
    cases = parse_cases(text)
    assert len(cases) == 2


def test_parse_cases_jsonl() -> None:
    text = (
        json.dumps({"actual": "a", "expected": "a"})
        + "\n"
        + json.dumps({"actual": "b", "expected": "b"})
    )
    cases = parse_cases(text)
    assert len(cases) == 2


def test_parse_cases_empty() -> None:
    assert parse_cases("") == []
    assert parse_cases("   \n  \n  ") == []
