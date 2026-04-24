"""CLI smoke tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_eval_forge.cli import main


@pytest.fixture()
def cases_file(tmp_path: Path) -> Path:
    p = tmp_path / "cases.jsonl"
    lines = [
        json.dumps({"id": "c1", "actual": "hello world", "expected": "hello world"}),
        json.dumps({"id": "c2", "actual": "hello", "expected": "goodbye"}),
    ]
    p.write_text("\n".join(lines))
    return p


def test_cli_score_json_output(cases_file: Path, capsys: pytest.CaptureFixture) -> None:
    rc = main(["score", str(cases_file)])
    assert rc == 1  # one case fails
    data = json.loads(capsys.readouterr().out)
    assert data["summary"]["total"] == 2
    assert data["summary"]["passed"] == 1


def test_cli_score_markdown_output(cases_file: Path, capsys: pytest.CaptureFixture) -> None:
    rc = main(["score", str(cases_file), "--format", "markdown"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "AI Eval Forge Report" in out
    assert "| Case |" in out
    assert "c1" in out and "c2" in out


def test_cli_all_passing_exits_zero(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    f = tmp_path / "pass.jsonl"
    f.write_text(json.dumps({"actual": "x", "expected": "x"}))
    rc = main(["score", str(f)])
    assert rc == 0


def test_cli_missing_file(capsys: pytest.CaptureFixture) -> None:
    rc = main(["score", "/does/not/exist"])
    assert rc == 2


def test_cli_accepts_json_array(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    f = tmp_path / "arr.json"
    f.write_text(json.dumps([{"actual": "x", "expected": "x"}, {"actual": "y", "expected": "y"}]))
    rc = main(["score", str(f)])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["summary"]["total"] == 2
