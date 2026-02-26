# Consolidated Reducer Validation Report (Critical Consolidation)

Date: 2026-02-26
Sources:
- `validations/reducers/reports/OpenLineage_reducer_validation.json`
- `validations/reducers/reports/commons_lang_reducer_validation.json`
- `validations/reducers/reports/fastapi_reducer_validation.json`
- `validations/reducers/reports/nest_reducer_validation.json`

## Executive Verdict
- Contract-constrained validation remains stable at workflow level.
- All configured repos pass hard and diagnostic gates.
- Strict policy parity remains clean; bottlenecks are calibration-driven.

## Cross-Repo Snapshot (Regenerated)
| Repo | Hard Passed | Diagnostic Failures | Strict Contract Precision | Strict Contract Recall | Overreach | Expanded Full Precision | Expanded Full Recall | Strict Parity Gate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| OpenLineage | True | 0 | 0.939394 | 0.991533 | 0.060606 | 0.954545 | 0.836719 | True |
| commons_lang | True | 0 | 0.985129 | 0.993631 | 0.014871 | 0.988185 | 0.952297 | True |
| fastapi | True | 0 | 0.979132 | 0.992494 | 0.020868 | 0.979132 | 0.964203 | True |
| nest | True | 0 | 0.919612 | 0.992615 | 0.080388 | 0.949829 | 0.861873 | True |

## Main Stress Points (Current)

### 1) Callable precision imbalance remains the top issue
- fastapi method precision: `0.270833` (tp/fp/fn=`13/35/0`)
- nest function precision: `0.391304` (tp/fp/fn=`36/56/5`)
- OpenLineage method precision: `0.724324` (tp/fp/fn=`134/51/6`)
- nest method precision: `0.726708` (tp/fp/fn=`117/44/5`)
- fastapi function precision: `0.776596` (tp/fp/fn=`73/21/0`)

### 2) Strict vs expanded recall gaps
- OpenLineage strict recall `0.991533` -> expanded full recall `0.836719` (delta `0.154815`)
- nest strict recall `0.992615` -> expanded full recall `0.861873` (delta `0.130743`)
- commons_lang strict recall `0.993631` -> expanded full recall `0.952297` (delta `0.041334`)
- fastapi strict recall `0.992494` -> expanded full recall `0.964203` (delta `0.028291`)

### 3) Independent strict candidate scarcity/ambiguity
- dropped: `{'no_candidates': 4966, 'unique_without_provenance': 3728, 'ambiguous_no_in_scope_candidate': 615, 'ambiguous_multiple_in_scope_candidates': 72}`
- accepted: `{'module_scoped': 533, 'import_narrowed': 372}`

### 4) Bi-directional disagreement
- `core_overresolution=886`
- `independent_overprojection=588`
- `core_missed_resolution=0`
- `normalization_contract_mismatch=0`

## Contract Boundary Signals (Current)
- OpenLineage: `independent_static_limitation_edges=217`, `contract_exclusion_edges=3057`, `contract_leakage_rate=0.078341`
- commons_lang: `independent_static_limitation_edges=227`, `contract_exclusion_edges=1716`, `contract_leakage_rate=0.066079`
- fastapi: `independent_static_limitation_edges=86`, `contract_exclusion_edges=3919`, `contract_leakage_rate=0.000000`
- nest: `independent_static_limitation_edges=308`, `contract_exclusion_edges=732`, `contract_leakage_rate=0.172078`

## Bottom Line
- Strict conformance and policy parity are stable.
- Remaining quality gap is resolver calibration under ambiguity and limitation-heavy regions.
- Next gains should prioritize callable precision recovery and dropped-candidate reduction.
