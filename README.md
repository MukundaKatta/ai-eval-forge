# ai-eval-forge

[![CI](https://github.com/MukundaKatta/ai-eval-forge/actions/workflows/ci.yml/badge.svg)](https://github.com/MukundaKatta/ai-eval-forge/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/ai-eval-forge.svg)](https://pypi.org/project/ai-eval-forge/)
[![Python](https://img.shields.io/pypi/pyversions/ai-eval-forge.svg)](https://pypi.org/project/ai-eval-forge/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Zero-dependency eval harness for LLM and agent regression testing. Score outputs with `exact`, `contains`, `regex`, `token_f1`, `json_valid`, `json_field`, and `citation_coverage` checks. Ships a CLI and a small library API. No runtime dependencies — pure stdlib.

Python port of the [`@mukundakatta/ai-eval-forge`](https://www.npmjs.com/package/@mukundakatta/ai-eval-forge) npm package. Same check types, same output shape — cases files you wrote for the npm version work here unchanged.

## Install

```bash
pip install ai-eval-forge
```

## Run the CLI

```bash
aef score cases.jsonl
# or
ai-eval-forge score cases.jsonl --format markdown
```

Exits `0` on all pass, `1` on any failures, `2` on bad input.

## Case file format

Each case is a JSON object. The file can be either a JSON array or JSONL (one object per line).

```jsonl
{"id": "greeting", "actual": "hello world", "expected": "hello world"}
{"id": "json-output", "actual": "{\"user\":{\"name\":\"Alice\"}}", "checks":[{"type":"json_field","path":"user.name","value":"Alice"}]}
{"id": "cited", "actual": "See [src1] and [src2].", "sources":[{"id":"src1"},{"id":"src2"}], "checks":[{"type":"citation_coverage","min":1}]}
```

## Check types

| Type | What it does |
|---|---|
| `exact` | Normalized (lowercase, whitespace-collapsed) string equality. |
| `contains` | All listed substrings present in `actual`. Optional `caseSensitive`. |
| `regex` | Python regex match against `actual`. `flags` accepts `i`, `m`, `s`. |
| `token_f1` | F1 over lowercase alphanumeric tokens. Default check if none specified. |
| `json_valid` | `actual` parses as valid JSON. |
| `json_field` | Parse JSON, drill into `path`, deep-equal against `value`. |
| `citation_coverage` | Fraction of source IDs from `sources` that appear inside `actual`. |

Every check accepts `required` (default `true`) and `min` (default `1`). The case passes iff every required check has `score >= min`. The case's overall `score` is the average of all checks.

## Library API

```python
from ai_eval_forge import evaluate_suite, parse_cases, render_markdown
from pathlib import Path

cases = parse_cases(Path("cases.jsonl").read_text())
suite = evaluate_suite(cases)
print(render_markdown(suite))
print(f"Pass rate: {suite.summary.passRate:.0%}")
```

## Output shape (JSON)

```json
{
  "summary": {
    "total": 2,
    "passed": 1,
    "failed": 1,
    "passRate": 0.5,
    "averageScore": 0.82,
    "totalCostUsd": 0.0,
    "averageLatencyMs": 0
  },
  "cases": [
    {
      "id": "greeting",
      "passed": true,
      "score": 1.0,
      "checks": [{"type": "token_f1", "required": true, "passed": true, "score": 1.0, "min": 0.65, "detail": "token_f1=1.0"}],
      "meta": {"input": null, "tags": [], "costUsd": 0, "latencyMs": 0}
    }
  ]
}
```

## Differences from the npm version

- **`js_expression` check type is dropped.** The JS version lets you run a JavaScript expression against case context. Python's equivalent (`eval`) is harder to sandbox, so the Python port omits this check type rather than ship a half-sandbox. If you need custom logic, use `regex` or `json_field` — or extend the library via your own `run_check` wrapper.

Everything else matches the npm package 1:1: same check types, same scoring formulas, same summary fields, same exit codes, same CLI flags.

## Development

```bash
pip install -e '.[dev]'
pytest
```

## License

MIT.
