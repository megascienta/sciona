# Independent Parser Fixture Matrix

`fixture_matrix.json` is the source of truth for differential parser fixtures.

Each fixture entry defines:
- `id`: stable test identifier
- `language`: `python` / `typescript` / `java`
- `root`: fixture directory under `tests/fixtures/independent/`
- `file_path`: file parsed by the independent parser
- `module_qualified_name`: expected module qname input
- `assert_mode`: `exact` or `subset` comparison against `expected.json`
- `requires`: optional runtime requirements (`node`, `java_parser_toolchain`)
- `categories`: scenario tags used for QA coverage planning

This matrix is consumed by parameterized tests in
`tests/reducers/test_independent_parsers.py` to provide:
- parser-vs-expected differential checks
- per-fixture determinism checks (stable hash across repeated runs)

`expected.json` supports optional normalized expectations:
- `expected_normalized_calls`: list of normalized call-edge objects
- `expected_normalized_imports`: list of normalized import-edge objects

When present, matrix differential tests validate these fields with:
- exact matching for `assert_mode: "exact"`
- subset containment for `assert_mode: "subset"`
