# Consolidated Reducer Validation Report

Date: 2026-02-23  
Source reports:
- `experiments/reducers/reports/OpenLineage_reducer_validation.json`
- `experiments/reducers/reports/commons_lang_reducer_validation.json`
- `experiments/reducers/reports/fastapi_reducer_validation.json`
- `experiments/reducers/reports/nest_reducer_validation.json`

## 1. Executive Verdict
Internal integrity is strong across all four repositories:
- `invariants.hard_passed = True`
- `internal_integrity.projection.static_projection_precision/recall = 1.0/1.0`

So reducer outputs remain exact DB projections for sampled nodes.

## 2. Cross-Repo Results

| Repo | Lang mix | Hard Passed | Strict P | Strict R | Strict Overreach | Expanded Full P | Expanded Full R | Navigation Rel. | Reasoning Rel. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OpenLineage | Java+Python+TS | True | 0.8740 | 0.9490 | 0.1260 | 0.8779 | 0.8877 | 0.8889 | 0.4310 |
| commons_lang | Java | True | 0.9845 | 0.9904 | 0.0155 | 0.9849 | 0.9707 | 0.8475 | 0.6571 |
| fastapi | Python | True | 0.9977 | 0.9723 | 0.0023 | 0.9977 | 0.9452 | 0.9873 | 0.7537 |
| nest | TypeScript | True | 0.9470 | 0.9776 | 0.0530 | 0.9560 | 0.9113 | 0.9980 | 0.7252 |

Key interpretation:
- Strict contract alignment is strongest in FastAPI and weakest in OpenLineage/Nest precision.
- Expanded-full recall is lower than strict recall in all repos (expected), showing residual static-analysis boundary gap.
- Reasoning reliability is consistently the limiting practical metric; worst on OpenLineage.

## 3. Repository Diagnostics

### 3.1 OpenLineage (multi-language)
- Main issue cluster is callable resolution quality in functions/methods.
- Strict per-kind:
  - `function precision/recall = 0.458 / 0.803`
  - `method precision/recall = 0.561 / 0.717`
- Diagnostic gates fail (non-blocking):
  - contract recall threshold
  - overreach threshold
  - member recall threshold
- This is the only repo with current diagnostic threshold failures.

### 3.2 commons_lang (Java)
- Strong strict metrics globally (`P/R=0.985/0.990`, low overreach).
- Residual weakness remains in methods:
  - `method precision/recall = 0.804 / 0.812`
- Expanded high/full are effectively identical in this run (limited dynamic/relative-unresolved impact).

### 3.3 fastapi (Python)
- Best precision and lowest overreach.
- Primary residual gap is method/function recall:
  - `function recall = 0.872`
  - `method recall = 0.692`
- Expanded recall drops from 0.972 to 0.945, consistent with unresolved/dynamic in-repo limitations.

### 3.4 nest (TypeScript)
- High recall and near-perfect navigation reliability.
- Precision-side weakness persists:
  - strict precision `0.947`
  - strict overreach `0.053`
- Method quality is still weaker than class/module:
  - `method precision/recall = 0.796 / 0.832`

## 4. SCIONA Core Deficiencies

Priority 1: callable/member resolution depth
- Cross-repo evidence: function/method precision/recall is the weakest layer in every repo.
- Most acute in OpenLineage and Nest methods, FastAPI methods for recall.

Priority 2: TS overresolution / precision-side noise
- Evidence: Nest strict overreach remains materially higher than Java/Python baselines.

Priority 3: Python method recall under dynamic patterns
- Evidence: FastAPI strict method recall 0.692 despite near-perfect precision.

Priority 4: multi-language mixed-repo degradation
- Evidence: OpenLineage exhibits substantially worse callable-level quality than single-language repos.

Bottom line on core:
- Internal correctness/integrity is not the issue.
- Residual deficits are analysis-power limits in callable/member resolution.

## 5. Validation Workflow Deficiencies

Priority 1: expanded-truth scoring still coarse in interpretation
- Tiers exist, but report-level diagnostics still need sharper per-reason/per-kind explanation for triage.
- Example: high vs full recall deltas are present but not yet surfaced as decision-first “what changed and why”.

Priority 2: prompt reliability remains heuristic
- It is useful as a risk proxy, but not calibrated to task-labeled outcomes.
- Current values can rank repos but cannot be treated as empirical task success probability.

Priority 3: markdown still under-represents JSON richness
- JSON now contains many detailed splits (tiers, policy, per-language/kind micros).
- Consolidated report should keep exposing the most discriminative subset to avoid hidden diagnostics.

Priority 4: threshold portability across repo types
- Fixed diagnostics thresholds are stressed by multi-language/multi-framework repos (OpenLineage), suggesting need for profile-aware interpretation.

## 6. Practical Summary

1. Reducer/DB integrity is stable and reliable.
2. Main core technical debt is callable/member resolution quality.
3. Largest remaining variance is language/repo-shape dependent (multi-language repos hardest).
4. Validation workflow is now structurally stronger (strict vs expanded split), but interpretation/reporting remains the main workflow gap.
