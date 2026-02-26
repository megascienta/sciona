# Reducer Validation Workflow

## 1. Purpose
Validation answers two questions:
- Is reducer output an exact projection of SCIONA artifacts/DB for evaluated entities?
- Under strict shared contract, does independent evidence align with core output?

Primary use:
- correctness-of-implementation checks,
- controlled diagnostics for contract boundaries and ambiguity pressure.

## 2. Independence Boundary
Required:
- Independent logic lives under `validations/reducers/validation/independent/*`.
- No semantic reuse from SCIONA core language analyzers.
- Strict call selection policy is shared with contract constraints (same acceptance/drop semantics).

Allowed shared utilities:
- runtime/config/path helpers,
- reducer/DB adapters,
- generic dataclasses.

## 3. Canonical Baskets
Per node, evidence is split into canonical baskets:
- `contract_truth_edges`: in-contract resolvable truth.
- `independent_static_limitation_edges`: in-repo out-of-contract limitation evidence.
- `contract_exclusion_edges`: excluded by policy (`standard_call`, `external`).

Hard invariants enforce:
- basket partition (no overlap),
- basket count reconciliation,
- strict contract purity and resolvedness.

## 4. Pipeline
1. Load entities from artifacts/DB (`module/class/function/method`).
2. Stratified sampling by language/kind/size buckets.
3. Parse sampled files with independent parsers (Python/TypeScript/Java).
4. Normalize calls/imports and build candidate-only resolution context.
5. Apply strict shared contract selector.
6. Build canonical baskets and expanded diagnostic truth.
7. Score reducer/db vs strict and expanded channels.
8. Evaluate hard + diagnostic gates.
9. Emit machine JSON and compact human markdown.

## 5. Report Structure (Markdown)
Human report is intentionally compact:
1. `Run Verdict`
2. `Mismatch Source`
3. `Contract Boundary`
4. `Top Risks`
5. `Appendix`

Full details remain in JSON.

## 6. Gate Model
### 6.1 Hard gates (must pass)
- `gate_reducer_db_exact`
- `gate_aligned_scoring`
- `gate_parse_coverage`
- `gate_contract_truth_pure`
- `gate_contract_truth_resolved`
- `gate_parser_deterministic`
- `gate_no_duplicate_contract_edges`
- `gate_basket_partition`
- `gate_basket_counts_reconciled`
- `gate_scoped_call_normalization`
- `gate_strict_contract_parity`
- `gate_limitation_scope_clean`
- `gate_limitation_taxonomy_stable`
- `gate_strict_drop_taxonomy_stable`
- `gate_equal_contract_metrics_when_exact`

### 6.2 Diagnostic gates (non-blocking)
- `gate_typescript_relative_index_contract`
- `gate_class_truth_nonempty_rate`
- `gate_class_truth_match_rate`
- `gate_contract_recall_min`
- `gate_overreach_rate_max`
- `gate_member_call_recall_min`
- `gate_kind_precision_floors`

`invariants.hard_passed` reflects hard-gate status.

## 7. Key Diagnostics
- `contract_boundary`: limitation census, truncation profile, failure taxonomy, leakage.
- `parity_attribution`: separates pressure sources:
  - independent candidate-set pressure,
  - core selector pressure,
  - final edge mismatch attribution.
- `quality_gates.kind_precision_floors`: callable hotspot guardrail.

## 8. Metric Notes
Core formulas:
- precision: `tp / (tp + fp)`
- recall: `tp / (tp + fn)`
- strict overreach: `fp / (tp + fp)`
- divergence: `(fp + fn) / (tp + fp + fn)`

Interpretation:
- strict metrics are conformance-oriented,
- expanded/boundary metrics are descriptive diagnostics, not correctness targets.

## 9. JSON Surface (Top-Level)
- `report_schema_version`
- `summary`
- `invariants`
- `quality_gates`
- `internal_integrity`
- `static_contract_alignment`
- `contract_boundary`
- `parity_attribution`
- `enriched_truth_alignment`
- `enrichment_practical`
- `micro_metrics*`
- `strict_contract_diagnostics`
- `call_resolution_diagnostics`
- `per_node`

## 10. Run
```bash
conda run -n multiphysics \
python validations/reducers/reducer_validation.py \
  --repo-root /path/to/repo \
  --nodes 500 \
  --seed 20260221 \
  --stability-runs 2
```

## 11. Interpretation Order
1. Check `hard_passed`.
2. If hard-pass, inspect strict precision/recall/overreach.
3. Use `Mismatch Source` and `parity_attribution` to localize root cause.
4. Use `Contract Boundary` for applicability/limitation envelope.
5. Use `Top Risks` for next actions.

## 12. Limits
- Independent parsing is static and cannot model runtime behavior fully.
- Independent truth is deterministic proxy truth, not absolute truth.
- Expanded channels are diagnostic and intentionally non-gating.
- Java fixtures require `SCIONA_JAVAPARSER_JAR` + `SCIONA_JAVAPARSER_RUNNER_JAR` plus `java`.
- Build/update runner jar with:
```bash
bash validations/reducers/scripts/build_java_parser_runner.sh
```
