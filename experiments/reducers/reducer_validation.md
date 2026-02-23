# Reducer Validation Contract (Current)

## 1. Purpose
Repository-independent validation of SCIONA reducer outputs against:
- SCIONA DB projection (internal integrity), and
- independent strict-contract truth (external static alignment oracle).

Scope:
- module imports,
- class-defined methods,
- callable neighbors.

## 2. Independence Boundary
Validation truth must remain independent from SCIONA core analyzers.

Required:
- independent parsers and normalization in `experiments/reducers/validation/independent/*`.
- no semantic import from `src/sciona/code_analysis/core/extract/languages/*`.

Allowed shared utilities:
- runtime/config/path helpers,
- reducer/DB adapters,
- generic dataclasses.

## 3. Canonical Contract
Authoritative machine-readable contract:
- `experiments/reducers/validation/structural_contract.yaml`

Contract truth rules:
- calls: in-repo callable targets only,
- imports: in-repo modules only,
- excludes dynamic/unresolved/external and configured standard-call exclusions.

## 4. Pipeline
1. Load modules/classes/functions/methods from artifacts DB.
2. Stratified sample by language/kind/size buckets.
3. Parse sampled files with independent parsers (PY/TS/Java).
4. Canonicalize module names and normalize independent outputs.
5. Apply scoped call normalization (language + module local).
6. Build independent call-resolution context.
7. Build two channels:
- `contract_truth`: strict in-repo contract edges.
- `enrichment`: out-of-contract diagnostics.
8. Score per node:
- `reducer_vs_db`
- `reducer_vs_contract_truth`
- `db_vs_contract_truth`
9. Evaluate invariants (hard vs diagnostic).
10. Emit JSON + Markdown report.

## 5. Metric Layers
Report schema version is emitted as `report_schema_version`.

### 5.1 `internal_integrity` (hard-gated)
Question: Is SCIONA internally exact and deterministic?

Contains:
- `projection.static_projection_precision` (reducer vs DB)
- `projection.static_projection_recall` (reducer vs DB)
- determinism fields (`parser_stability_score`, gate)
- hard-gate statuses

Run validity (`internal_integrity.valid`) is based on hard gates only.

### 5.2 `static_contract_alignment` (external static quality)
Question: How well does reducer output match independent strict-contract truth?

Contains:
- `static_contract_precision`
- `static_contract_recall`
- `static_overreach_rate`
- `static_divergence_index`
- per-kind, per-edge-type, call-form breakdown

This is primary external quality, but diagnostic (non-blocking by default).

### 5.3 `enrichment_practical` (LLM-usefulness diagnostics)
Question: How stable is downstream prompt utility?

Contains:
- navigation/reasoning reliability
- coupling stability
- enrichment noise stats
- edge mix
- explicit reliability weights from config

Purely diagnostic; never hard-gates run validity.

## 6. Gates
### 6.1 Hard gates (blocking)
- `gate_reducer_db_exact`
- `gate_aligned_scoring`
- `gate_parse_coverage`
- `gate_contract_truth_pure`
- `gate_contract_truth_resolved`
- `gate_parser_deterministic`
- `gate_no_duplicate_contract_edges`
- `gate_scoped_call_normalization`
- `gate_equal_contract_metrics_when_exact`

### 6.2 Diagnostic gates (non-blocking by default)
- `gate_typescript_relative_index_contract`
- `gate_class_truth_nonempty_rate`
- `gate_class_truth_match_rate`
- `gate_contract_recall_min`
- `gate_overreach_rate_max`
- `gate_member_call_recall_min`

`invariants.passed` / `invariants.hard_passed` reflect hard gates.
Diagnostic failures are reported separately.

## 7. Formulas
- precision: `tp / (tp + fp)`
- recall: `tp / (tp + fn)`
- static overreach: `fp / (tp + fp)` from `reducer_vs_contract_truth`
- divergence: `(fp + fn) / (tp + fp + fn)`
- weighted reliability: `tp / (tp + fp_w*fp + fn_w*fn)`

The emitted `metric_definitions` map is canonical for name -> source -> formula.

## 8. Output Keys (Top Level)
- `report_schema_version`
- `summary`
- `invariants`
- `metric_definitions`
- `core_metrics`
- `internal_integrity`
- `static_contract_alignment`
- `enrichment_practical`
- micro metrics (`micro_metrics`, `micro_metrics_by_kind`, `micro_metrics_by_language`, `micro_metrics_by_language_and_kind`)
- diagnostics (`call_form_recall`, `edge_type_breakdown_reducer_vs_contract_truth`, `failure_examples_reducer_vs_contract_truth`, `out_of_contract_breakdown`, `mismatch_attribution_breakdown`)
- parser/stability/population/per-node payload blocks

## 9. Run
```bash
python experiments/reducers/reducer_validation.py \
  --repo-root /path/to/repo \
  --nodes 500 \
  --seed 20260221 \
  --stability-runs 2
```

## 10. Interpretation Rules
1. Validate `internal_integrity.valid` first.
2. If valid and `gate_reducer_db_exact=True`, reducer and DB are equivalent projection for evaluated nodes.
3. Use `static_contract_alignment` as external static quality verdict.
4. Use `enrichment_practical` only for prompt/use-case suitability decisions.
5. Use per-language and per-kind breakdowns before cross-repo conclusions.

## 11. Rollup Policy
Rollups are full rebuilt each run (correctness-first). Incremental rollup recompute is disabled by default.

## 12. Known Limits
- Independent parsers are static; no runtime dispatch modeling.
- Enrichment is best-effort diagnostics, outside strict contract scoring.
- Java fixture tests require `SCIONA_JAVAPARSER_JAR` + `java/javac`.
