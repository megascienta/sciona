# Consolidated Reducer Validation Report (Critical Consolidation)

Date: 2026-02-23
Sources:
- `experiments/reducers/reports/OpenLineage_reducer_validation.json`
- `experiments/reducers/reports/commons_lang_reducer_validation.json`
- `experiments/reducers/reports/fastapi_reducer_validation.json`
- `experiments/reducers/reports/nest_reducer_validation.json`

## Executive Verdict
- Contract-constrained validation is substantially improved and now stable at the workflow level.
- All four repos pass hard gates and diagnostic gates (`invariants.diagnostic_failures=[]`).
- Shared strict-contract parity solved (`gate_strict_contract_parity=true` in all four repos).
- Remaining gaps are not contract-layer drift; they are resolver quality/calibration stress points (precision imbalance by repo/language, enrichment recall drop, unresolved volume).

## Cross-Repo Snapshot (Regenerated)
| Repo | Hard Passed | Strict Contract Precision | Strict Contract Recall | Overreach | Expanded Full Precision | Expanded Full Recall | Strict Parity Gate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| OpenLineage | True | 0.977876 | 0.988372 | 0.022124 | 0.979646 | 0.830458 | True |
| commons_lang | True | 0.972917 | 0.998077 | 0.027083 | 0.973542 | 0.973339 | True |
| fastapi | True | 0.979132 | 0.992494 | 0.020868 | 0.979132 | 0.964203 | True |
| nest | True | 0.932951 | 0.993895 | 0.067049 | 0.962751 | 0.870016 | True |

## Main Stress Points (Current)

### 1) Precision imbalance in callable kinds (still major)
- commons_lang method precision: `0.295455` (tp/fp/fn=`39/93/3`)
- fastapi method precision: `0.270833` (tp/fp/fn=`13/35/0`)
- nest function precision: `0.610169` (tp/fp/fn=`72/46/3`)

Impact:
- Even with high recall, FP pressure keeps overreach elevated in affected repos.

### 2) Nest overreach remains highest
- Nest strict overreach: `0.067049` (highest among four repos).

Impact:
- Contract-safe but still over-resolving in practical terms.

### 3) Strict vs enrichment gap remains large in OpenLineage and Nest
- OpenLineage strict recall `0.988372` -> expanded full recall `0.830458`
- Nest strict recall `0.993895` -> expanded full recall `0.870016`

Impact:
- Practical limitation coverage (dynamic/unresolved areas) still lags despite strong strict-contract metrics.

### 4) Independent strict candidate scarcity/ambiguity remains high
Aggregate independent strict diagnostics:
- dropped: `no_candidates=3693`, `unique_without_provenance=2235`, `ambiguous_no_in_scope_candidate=555`, `ambiguous_multiple_in_scope_candidates=30`
- accepted: `module_scoped=461`, `import_narrowed=227`

Impact:
- Candidate generation + deterministic narrowing still leaves large unresolved space.

### 5) Bi-directional disagreement is still large (though contract parity is stable)
Aggregate mismatch attribution:
- `core_overresolution=3957`
- `independent_overprojection=3671`
- `core_missed_resolution=0`
- `normalization_contract_mismatch=0`

Impact:
- Core and independent paths still disagree substantially on edge sets in difficult regions.

## Concrete Improvements (ROI)

### High ROI
1. Calibrate method/function precision in per-language adapters using dropped-reason budgets and FP clusters.
- Priority repos: Nest, commons_lang, fastapi.

2. Add focused fixtures for FP-heavy patterns (especially Java method/import ambiguity and Python method overresolution).
- Gate on reduction in `core_overresolution` and method FP counts.

3. Add repo-level precision floors by callable kind (not only micro aggregates).
- Prevent “high recall + local precision collapse” from hiding under global metrics.

### Medium ROI
1. Add per-reason strict diagnostics trend charting in reports (`no_candidates`, `unique_without_provenance`, `ambiguous_*`).
2. Split mismatch attribution by language/kind in consolidated report to localize tuning.
3. Keep enrichment as non-gating but track strict->expanded recall deltas as explicit warning thresholds.

## Bottom Line
- Contract parity and strict-contract stability are now in good shape.
- The remaining bottleneck is quality calibration under ambiguity, not contract inconsistency.
- Next gains should target precision recovery (especially methods/functions) and unresolved candidate reduction.
