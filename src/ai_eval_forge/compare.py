"""Compare two suite-result JSON files and report regressions + improvements.

Input files are the JSON produced by ``aef score <file>``. Compares by case id
and yields a structured diff plus an exit code.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field


@dataclass
class CaseDiff:
    id: str
    baseline_passed: bool
    current_passed: bool
    baseline_score: float
    current_score: float

    @property
    def score_delta(self) -> float:
        return round(self.current_score - self.baseline_score, 4)

    @property
    def status(self) -> str:
        if self.baseline_passed and not self.current_passed:
            return "regression"
        if not self.baseline_passed and self.current_passed:
            return "improvement"
        if self.score_delta > 0:
            return "score_up"
        if self.score_delta < 0:
            return "score_down"
        return "unchanged"


@dataclass
class CompareResult:
    regressions: list[CaseDiff] = field(default_factory=list)
    improvements: list[CaseDiff] = field(default_factory=list)
    score_changes: list[CaseDiff] = field(default_factory=list)
    unchanged: int = 0
    added_ids: list[str] = field(default_factory=list)
    removed_ids: list[str] = field(default_factory=list)
    baseline_pass_rate: float = 0.0
    current_pass_rate: float = 0.0

    @property
    def has_regressions(self) -> bool:
        return bool(self.regressions) or bool(self.removed_ids)

    @property
    def pass_rate_delta(self) -> float:
        return round(self.current_pass_rate - self.baseline_pass_rate, 4)

    def to_dict(self) -> dict:
        return {
            "regressions": [asdict(d) for d in self.regressions],
            "improvements": [asdict(d) for d in self.improvements],
            "score_changes": [asdict(d) for d in self.score_changes],
            "unchanged": self.unchanged,
            "added_ids": self.added_ids,
            "removed_ids": self.removed_ids,
            "baseline_pass_rate": self.baseline_pass_rate,
            "current_pass_rate": self.current_pass_rate,
            "pass_rate_delta": self.pass_rate_delta,
            "has_regressions": self.has_regressions,
        }


def _index_cases(suite_json: dict) -> dict[str, dict]:
    return {c.get("id", f"case-{i}"): c for i, c in enumerate(suite_json.get("cases", []))}


def compare_suites(baseline: dict, current: dict) -> CompareResult:
    """Compare two suite-result dicts (as produced by evaluate_suite().to_dict())."""
    result = CompareResult(
        baseline_pass_rate=baseline.get("summary", {}).get("passRate", 0.0),
        current_pass_rate=current.get("summary", {}).get("passRate", 0.0),
    )

    base_index = _index_cases(baseline)
    curr_index = _index_cases(current)

    result.added_ids = sorted(set(curr_index) - set(base_index))
    result.removed_ids = sorted(set(base_index) - set(curr_index))

    for case_id in sorted(set(base_index) & set(curr_index)):
        b = base_index[case_id]
        c = curr_index[case_id]
        diff = CaseDiff(
            id=case_id,
            baseline_passed=bool(b.get("passed")),
            current_passed=bool(c.get("passed")),
            baseline_score=float(b.get("score", 0)),
            current_score=float(c.get("score", 0)),
        )
        status = diff.status
        if status == "regression":
            result.regressions.append(diff)
        elif status == "improvement":
            result.improvements.append(diff)
        elif status in ("score_up", "score_down"):
            result.score_changes.append(diff)
        else:
            result.unchanged += 1

    # Sort for deterministic output
    result.regressions.sort(key=lambda d: (d.score_delta, d.id))
    result.improvements.sort(key=lambda d: (-d.score_delta, d.id))
    result.score_changes.sort(key=lambda d: (d.score_delta, d.id))
    return result


def compare_files(baseline_path: str, current_path: str) -> CompareResult:
    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline = json.load(f)
    with open(current_path, "r", encoding="utf-8") as f:
        current = json.load(f)
    return compare_suites(baseline, current)


def render_compare_markdown(r: CompareResult, baseline_label: str = "baseline", current_label: str = "current") -> str:
    lines: list[str] = []
    lines.append(f"# AI Eval Forge Comparison")
    lines.append("")
    lines.append(
        f"Pass rate: {baseline_label} {r.baseline_pass_rate:.0%} → "
        f"{current_label} {r.current_pass_rate:.0%} "
        f"({'+' if r.pass_rate_delta >= 0 else ''}{r.pass_rate_delta:.0%})"
    )
    lines.append("")
    lines.append(f"- Regressions: **{len(r.regressions)}**")
    lines.append(f"- Improvements: **{len(r.improvements)}**")
    lines.append(f"- Score changes (no flip): {len(r.score_changes)}")
    lines.append(f"- Unchanged: {r.unchanged}")
    lines.append(f"- Added cases: {len(r.added_ids)}")
    lines.append(f"- Removed cases: {len(r.removed_ids)}")
    lines.append("")

    if r.regressions:
        lines.append("## Regressions")
        lines.append("")
        lines.append("| Case | Score | Was passing | Now passing |")
        lines.append("| --- | ---: | :---: | :---: |")
        for d in r.regressions:
            lines.append(
                f"| {d.id} | {d.baseline_score} → {d.current_score} ({d.score_delta:+}) | yes | **no** |"
            )
        lines.append("")

    if r.improvements:
        lines.append("## Improvements")
        lines.append("")
        lines.append("| Case | Score | Was passing | Now passing |")
        lines.append("| --- | ---: | :---: | :---: |")
        for d in r.improvements:
            lines.append(
                f"| {d.id} | {d.baseline_score} → {d.current_score} ({d.score_delta:+}) | no | **yes** |"
            )
        lines.append("")

    if r.score_changes:
        lines.append("## Score changes (still-passing or still-failing)")
        lines.append("")
        for d in r.score_changes:
            lines.append(f"- `{d.id}`: {d.baseline_score} → {d.current_score} ({d.score_delta:+})")
        lines.append("")

    if r.added_ids:
        lines.append("## New cases")
        lines.append("")
        for cid in r.added_ids:
            lines.append(f"- `{cid}`")
        lines.append("")

    if r.removed_ids:
        lines.append("## Removed cases")
        lines.append("")
        for cid in r.removed_ids:
            lines.append(f"- `{cid}`")
        lines.append("")

    return "\n".join(lines) + "\n"
