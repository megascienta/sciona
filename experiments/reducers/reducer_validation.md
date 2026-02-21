# Reducer Validation Contract (Current)

## 1. Purpose
This workflow validates SCIONA reducer outputs against:
- SCIONA DB graph queries (internal consistency check), and
- Independent parser truth (external reference).

The goal is not to prove "all code semantics"; the goal is to validate the enforced structural contract for:
- module imports,
- class defined methods,
- callable neighbors.

## 2. Canonical Contract
Authoritative machine-readable contract:
- `experiments/reducers/validation/structural_contract.yaml`

Key contract rules:
- Calls use terminal identifiers and must resolve to in-repo targets for in-contract scoring.
- Imports must resolve to in-repo modules for in-contract scoring.
- Out-of-contract includes unresolved/external/dynamic and configured standard calls.

## 3. Source-of-Truth Model
Per sampled node, the workflow constructs three edge sets:
1. `reducer_edges`: SCIONA reducer output.
2. `db_edges`: direct graph DB query output.
3. `independent_full` + `independent_filtered`:
   - `full`: all independent parser edges for the node scope.
   - `filtered`: independent edges that satisfy SCIONA contract.

Independent edges are deduplicated as neighbor edges (not callsite frequency).

## 4. Validation Pipeline
1. Load nodes from artifact/core DB.
2. Stratified sampling by language/kind/buckets.
3. Parse sampled files with independent parsers (Python/TS/Java).
4. Normalize independent outputs into SCIONA comparison shape.
5. Build independent call-resolution context.
6. Compute per-node metrics for:
   - reducer vs db
   - db vs independent full
   - reducer vs independent filtered
   - reducer vs independent full
7. Enforce hard invariants.
8. Emit JSON + Markdown reports.

## 5. Hard Invariants (Run-Gating)
The run is valid only when all pass:
- `gate_reducer_db_exact`
- `gate_aligned_scoring`
- `gate_parse_coverage`
- `gate_filter_subset`
- `gate_filter_resolved`
- `gate_parser_deterministic`
- `gate_no_duplicate_contract_edges`
- `gate_equal_full_metrics_when_exact`

Interpretation:
- If any gate fails, analysis is invalid until fixed.
- `reducer_vs_db == exact` is mandatory; reducer is a DB projection.

## 6. Core Metrics (Decision Layer)
Primary metrics:
- `contract_recall`: reducer coverage of filtered independent truth.
- `full_recall`: reducer coverage of unfiltered independent truth.
- `overreach_rate`: reducer edges outside independent full truth.

Expected behavior:
- `contract_recall` should be near 1.0 if SCIONA contract coverage is strong.
- `full_recall` is expected to be lower than `contract_recall`.
- `overreach_rate` should be low; high values indicate resolver/schema mismatch risk.

## 7. Determinism
`--stability-runs` reruns independent parsing and hashes normalized outputs.
- `stability_score = 1.0` means deterministic parser output across reruns.
- Hashes are stored in `stability_hashes`.

This is independent-parser determinism, not structural-index hash stability.

## 8. Output Schema (Current)
Main report keys:
- `summary`
- `invariants`
- `core_metrics`
- `micro_metrics`
- `edge_type_breakdown_reducer_vs_independent_full`
- `out_of_contract_breakdown`
- `independent_totals`
- `independent_coverage_by_language`
- `stability_score`, `stability_hashes`, `stability_error`
- `per_node`

Paths:
- `experiments/reducers/reports/<repo>_reducer_validation.json`
- `experiments/reducers/reports/<repo>_reducer_validation.md`

## 9. Running
```bash
python experiments/reducers/reducer_validation.py \
  --repo-root /path/to/repo \
  --nodes 500 \
  --seed 20260221 \
  --stability-runs 3
```

## 10. Interpretation Rules
- First check invariants; if any fail, do not trust metric comparisons.
- If invariants pass and `reducer_vs_db` is exact, then reducer and DB are equivalent for evaluated nodes.
- Differences vs independent truth then indicate contract/scope/resolution gaps, not reducer-vs-DB divergence.
- Use `out_of_contract_breakdown` to separate expected contract exclusions from actionable misses.

## 11. Known Limits
- Independent parsers are static and contract-driven; they do not model runtime dispatch.
- Cross-language semantic equivalence is constrained by parser/resolution quality.
- Worktree-dirty repositories can diverge from last committed SCIONA snapshot; rebuild/index hygiene still matters.
