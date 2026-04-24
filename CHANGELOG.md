# Changelog

## [0.1.0] - 2026-04-24

### Added
- Initial release. Python port of `@mukundakatta/ai-eval-forge` v0.1.0 (npm).
- CLI `aef` and `ai-eval-forge` with a `score` subcommand.
- Library API: `evaluate_case`, `evaluate_suite`, `run_check`, `parse_cases`, `token_f1`, `render_markdown`, and dataclasses (`CaseResult`, `CheckResult`, `SuiteResult`, `Summary`).
- Check types: `exact`, `contains`, `regex`, `token_f1` (default), `json_valid`, `json_field`, `citation_coverage`.
- Output formats: JSON and Markdown.
- Zero runtime dependencies.

### Notes on parity with the npm package
- The `js_expression` check type from the npm package is deliberately not ported in this release. Python's equivalent (`eval`) is harder to sandbox safely. Use `regex` or `json_field` for custom logic.
- All other check types, scoring formulas, and summary fields match the npm implementation 1:1. Cases files written for the npm version work here unchanged, minus `js_expression` entries.
