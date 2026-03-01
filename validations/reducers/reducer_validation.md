# Reducer Validation Workflow

## Purpose
This workflow validates reducer behavior against two independent references:
1. Core/artifact DB parity (`Q1`, exactness required).
2. Independent parser overlap inside strict static contract (`Q2`, quality gate).

It also reports descriptive out-of-contract behavior (`Q3`) and unresolved-static defect rates.

## Non-Goals
- No legacy precision/recall report model.
- No validator-owned contract semantics.
- No validator-owned call-candidate narrowing heuristics.

## Canonical Set Model
All metrics are edge-set metrics (not node-set metrics).

- `S1`: reducer contract edge set (reference in Q2).
- `S2`: independent constrained edge set (candidate in Q2).
- `S2_syntax`: independent syntax-only baseline set (diagnostic).
- `S3_non_static`: non-static edges beyond contract (descriptive).
- `S_unresolved_static`: unresolved static-looking edges (defect bucket).

Definitions:
- `intersection = |S1 ∩ S2|`
- `missing = |S1 \ S2|`
- `spillover = |S2 \ S1|`
- `missing_rate_i = |S1_i \ S2_i| / |S1_i|`
- `spillover_rate_i = |S2_i \ S1_i| / |S1_i|`
- `mutual_accuracy_i = |S1_i ∩ S2_i| / |S1_i ∪ S2_i|`
- `q3_non_static_rate_i = |S3_non_static_i| / |S1_i|`
- `unresolved_static_rate_i = |S_unresolved_static_i| / |S1_i|`

## Questions

### Q1: Reducers vs DB (Exact)
Pass requires per aggregate:
- `missing_count == 0`
- `spillover_count == 0`

### Q2: Reducers vs Independent (In-Contract)
Primary gate metrics (weighted aggregate):
- `weighted_mutual_accuracy >= 0.99`
- `weighted_missing_rate <= 0.01`
- `weighted_spillover_rate <= 0.01`

Diagnostic metrics (non-gating):
- `avg_mutual_accuracy`
- `avg_missing_rate`
- `avg_spillover_rate`

Q2 is evaluated only on scored nodes with non-null contract-set metrics.

### Q2 Syntax Baseline (Diagnostic)
`set_q2_reducer_vs_independent_syntax` is emitted for comparison only and is not the gate.

### Q3: Beyond Contract Envelope (Descriptive)
Reported only:
- `avg_non_static_rate_percent`
- `by_semantic_type_non_static_avg_percent`
- `decorator_rate_percent`
- `dynamic_dispatch_rate_percent`

### Unresolved-Static Defect (Quality Defect, Not Q3 Gate)
- `unresolved_static_avg_percent`
- target: `0`

## Core-First Pipeline (Current)
1. Load entities (`module`, `class`, `function`, `method`) from artifact/core DB.
2. Stratified sample by language/kind.
3. Parse sampled files with independent parsers (Python/TS/Java) to raw syntax facts.
4. Normalize calls via core call-identifier normalization pipeline.
5. Normalize imports via core language import normalization adapters.
6. Build minimal call-resolution context:
   - `symbol_index`
   - `module_lookup`
   - `import_targets`
7. Apply strict contract acceptance through core strict selector (`select_strict_call_candidate`).
8. Build per-entity sets (`Q1`, `Q2`, `Q2_syntax`, `Q3`, unresolved-static).
9. Aggregate and emit JSON + Markdown reports.

## Important Invariants
- Validator does not redefine contract semantics.
- Call acceptance semantics are delegated to core strict contract selector.
- Validator-specific resolution artifacts (`receiver_bindings`, alias maps, class/method side indexes) are removed from call-resolution payload and do not affect Q2 contract overlap.
- Q3 is descriptive and must not be interpreted as pass/fail for contract parity.

## Report Contract (Current)
Top-level keys:
- `report_schema_version`
- `summary`
- `sampling`
- `invariants`
- `quality_gates`
- `per_node`
- `questions`

Per-node keys (current):
- `set_q1_reducer_vs_db`
- `set_q2_reducer_vs_independent_contract`
- `set_q2_reducer_vs_independent_syntax`
- `basket2_edges`
- `q2_filtering_stats`
- `q2_ground_truth_diagnostics`
- `q2_node_rates`
- `q3_non_static_rate_percent`
- `unresolved_static_rate_percent`

Legacy keys forbidden:
- `metrics_reducer_vs_db`
- `metrics_reducer_vs_contract`
- `metrics_db_vs_contract`

## Run
```bash
conda run -n multiphysics \
python validations/reducers/reducer_validation.py \
  --repo-root /path/to/repo \
  --nodes 500 \
  --seed 20260219
```

## Interpretation Guidance
- `Q1 pass + Q2 fail` usually means reducers/DB are internally consistent but independent parser overlap (within contract) is still incomplete.
- High unresolved-static defect implies genuine static-resolution gaps or unresolved normalization boundaries.
- `in_repo_unresolved*` limitation reasons are selector-drop diagnostics; use the
  suffix reason to distinguish ambiguity/provenance gaps from no-candidate cases.
- Use `top_mismatch_signatures` and `strict_contract_candidate_count_histogram` first; do not infer architectural defects from aggregate metrics alone.
