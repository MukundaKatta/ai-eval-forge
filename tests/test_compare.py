"""Tests for the compare subcommand."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_eval_forge.cli import main
from ai_eval_forge.compare import compare_suites, render_compare_markdown


def _suite(cases: list[dict], pass_rate: float | None = None) -> dict:
    if pass_rate is None:
        passed = sum(1 for c in cases if c["passed"])
        pass_rate = passed / len(cases) if cases else 0.0
    return {
        "summary": {
            "total": len(cases),
            "passed": sum(1 for c in cases if c["passed"]),
            "failed": sum(1 for c in cases if not c["passed"]),
            "passRate": pass_rate,
        },
        "cases": cases,
    }


def _case(cid: str, passed: bool, score: float) -> dict:
    return {"id": cid, "passed": passed, "score": score}


def test_no_changes_no_regressions() -> None:
    cases = [_case("a", True, 1.0), _case("b", True, 0.9)]
    result = compare_suites(_suite(cases), _suite(cases))
    assert not result.has_regressions
    assert result.unchanged == 2
    assert result.regressions == []
    assert result.improvements == []


def test_regression_pass_to_fail() -> None:
    base = [_case("a", True, 1.0)]
    curr = [_case("a", False, 0.3)]
    result = compare_suites(_suite(base), _suite(curr))
    assert result.has_regressions
    assert len(result.regressions) == 1
    assert result.regressions[0].id == "a"


def test_improvement_fail_to_pass() -> None:
    base = [_case("a", False, 0.4)]
    curr = [_case("a", True, 0.95)]
    result = compare_suites(_suite(base), _suite(curr))
    assert not result.has_regressions
    assert len(result.improvements) == 1


def test_score_change_without_flip() -> None:
    base = [_case("a", True, 0.80)]
    curr = [_case("a", True, 0.85)]
    result = compare_suites(_suite(base), _suite(curr))
    assert not result.has_regressions
    assert len(result.score_changes) == 1
    assert result.score_changes[0].status == "score_up"


def test_added_and_removed_cases() -> None:
    base = [_case("a", True, 1.0), _case("b", True, 1.0)]
    curr = [_case("a", True, 1.0), _case("c", True, 1.0)]
    result = compare_suites(_suite(base), _suite(curr))
    assert result.added_ids == ["c"]
    assert result.removed_ids == ["b"]
    # removed cases are treated as regressions
    assert result.has_regressions


def test_pass_rate_delta_computed() -> None:
    base = _suite([_case("a", True, 1.0), _case("b", False, 0.0)])
    curr = _suite([_case("a", True, 1.0), _case("b", True, 1.0)])
    result = compare_suites(base, curr)
    assert abs(result.pass_rate_delta - 0.5) < 1e-6


def test_markdown_renders_regressions_block() -> None:
    base = [_case("a", True, 1.0), _case("b", True, 0.95)]
    curr = [_case("a", False, 0.2), _case("b", True, 0.95)]
    result = compare_suites(_suite(base), _suite(curr))
    md = render_compare_markdown(result)
    assert "# AI Eval Forge Comparison" in md
    assert "## Regressions" in md
    assert "| a |" in md


def test_cli_compare_json(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    base_file = tmp_path / "base.json"
    curr_file = tmp_path / "curr.json"
    base_file.write_text(json.dumps(_suite([_case("a", True, 1.0)])))
    curr_file.write_text(json.dumps(_suite([_case("a", False, 0.3)])))

    rc = main(["compare", str(base_file), str(curr_file), "--format", "json"])
    assert rc == 1
    data = json.loads(capsys.readouterr().out)
    assert data["has_regressions"]
    assert len(data["regressions"]) == 1


def test_cli_compare_markdown(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    base_file = tmp_path / "base.json"
    curr_file = tmp_path / "curr.json"
    base_file.write_text(json.dumps(_suite([_case("a", True, 1.0)])))
    curr_file.write_text(json.dumps(_suite([_case("a", True, 1.0)])))

    rc = main(["compare", str(base_file), str(curr_file)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "AI Eval Forge Comparison" in out


def test_cli_compare_missing_file(tmp_path: Path) -> None:
    base_file = tmp_path / "base.json"
    base_file.write_text(json.dumps(_suite([_case("a", True, 1.0)])))
    rc = main(["compare", str(base_file), "/does/not/exist.json"])
    assert rc == 2


def test_cli_compare_bad_json(tmp_path: Path) -> None:
    base = tmp_path / "base.json"
    curr = tmp_path / "curr.json"
    base.write_text("{ broken")
    curr.write_text("{}")
    rc = main(["compare", str(base), str(curr)])
    assert rc == 2
