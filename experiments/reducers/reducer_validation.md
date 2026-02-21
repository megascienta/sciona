# Reducer Validation Contract (Current)

## 1. Purpose
This workflow validates SCIONA reducer outputs against:
- SCIONA DB graph queries (internal consistency check), and
- independent parser truth (external reference).

The scope is strict structural contract validation for:
- module imports,
- class defined methods,
- callable neighbors.

## 2. Independence Boundary
Validation must remain parser-independent from SCIONA core semantics.

Required boundary:
- `experiments/reducers/validation/independent/*` and validation contract resolution use independent implementations.
- No semantic import from `src/sciona/code_analysis/core/extract/languages/*`.

Allowed shared dependencies:
- runtime/config/path helpers,
- DB/reducer query adapters,
- generic dataclasses/utilities.

## 3. Canonical Contract
Authoritative machine-readable contract:
- `experiments/reducers/validation/structural_contract.yaml`

Key contract rules:
- Calls use terminal identifiers and must resolve to in-repo targets for in-contract scoring.
- Imports must resolve to in-repo modules for in-contract scoring.
- Out-of-contract includes unresolved/external/dynamic and configured standard calls.

## 4. Validation Pipeline
1. Load nodes from artifact/core DB.
2. Stratified sampling by language/kind/buckets.
3. Parse sampled files with independent parsers (Python/TS/Java).
4. Canonicalize module names and normalize independent outputs into SCIONA comparison shape.
5. Apply independent scoped call normalization (language + module scope).
6. Build independent call-resolution context.
7. Compute per-node metrics for:
   - reducer vs db
   - db vs independent full
   - reducer vs independent filtered
   - reducer vs independent full
8. Enforce hard invariants.
9. Emit JSON + Markdown reports.

## 5. Hard Invariants (Run-Gating)
The run is valid only when all pass:
- `gate_reducer_db_exact`
- `gate_aligned_scoring`
- `gate_parse_coverage`
- `gate_filter_subset`
- `gate_filter_resolved`
- `gate_parser_deterministic`
- `gate_no_duplicate_contract_edges`
- `gate_typescript_relative_index_contract`
- `gate_class_truth_nonempty_rate`
- `gate_scoped_call_normalization`
- `gate_equal_full_metrics_when_exact`

Interpretation:
- If any gate fails, analysis is invalid until fixed.
- `reducer_vs_db == exact` is mandatory; reducer is a DB projection.

## 6. Core Metrics (Decision Layer)
Primary metrics:
- `contract_recall`: reducer coverage of filtered independent truth.
- `full_recall`: reducer coverage of unfiltered independent truth.
- `overreach_rate`: reducer edges outside independent full truth.

Auxiliary quality metrics:
- `quality_gates.class_truth_nonempty_rate`
- `quality_gates.scoped_call_normalization_ok`
- `micro_metrics_by_kind` (module/class/function/method)

## 7. Determinism
`--stability-runs` reruns independent parsing and hashes normalized outputs.
- `stability_score = 1.0` means deterministic parser output across reruns.
- Hashes are stored in `stability_hashes`.

## 8. Output Schema (Current)
Main report keys:
- `summary`
- `invariants`
- `core_metrics`
- `micro_metrics`
- `micro_metrics_by_kind`
- `quality_gates`
- `edge_type_breakdown_reducer_vs_independent_full`
- `out_of_contract_breakdown`
- `independent_totals`
- `independent_coverage_by_language`
- `stability_score`, `stability_hashes`, `stability_error`
- `per_node`

## 9. Running
```bash
python experiments/reducers/reducer_validation.py \
  --repo-root /path/to/repo \
  --nodes 500 \
  --seed 20260221 \
  --stability-runs 2
```

## 10. Interpretation Rules
- First check invariants; if any fail, do not trust metric comparisons.
- If invariants pass and `reducer_vs_db` is exact, reducer and DB are equivalent for evaluated nodes.
- Differences vs independent truth then indicate contract/scope/resolution gaps.
- Use `micro_metrics_by_kind` and `quality_gates` before drawing language-level conclusions.

## 11. Rollup Policy
Artifact rollups are rebuilt fully each run (correctness-first).
Incremental rollup recompute is disabled by default.

## 12. Known Limits
- Independent parsers are static and contract-driven; they do not model runtime dispatch.
- Cross-language semantic equivalence is constrained by parser/resolution quality.
- Java independent parser fixture requires `SCIONA_JAVAPARSER_JAR` + `java/javac`.
