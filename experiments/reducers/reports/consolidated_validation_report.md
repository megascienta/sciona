# Consolidated Reducer Validation Report

Date: 2026-02-23  
Source reports:
- `experiments/reducers/reports/commons_lang_reducer_validation.json`
- `experiments/reducers/reports/fastapi_reducer_validation.json`
- `experiments/reducers/reports/nest_reducer_validation.json`

## 1. Executive Verdict
All three repositories pass hard validity:
- `invariants.hard_passed = True`
- `internal_integrity.projection.static_projection_precision/recall = 1.0/1.0`

So reducer output is an exact DB projection for sampled nodes in all three repos.

## 2. Cross-Repo Summary

| Repo | Language | Hard Passed | Strict Precision | Strict Recall | Strict Overreach | Expanded Precision | Expanded Recall | Navigation Reliability | Reasoning Reliability |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| commons_lang | Java | True | 0.9845 | 0.9904 | 0.0155 | 0.9851 | 0.9686 | 0.8475 | 0.6571 |
| fastapi | Python | True | 0.9977 | 0.9723 | 0.0023 | 0.9977 | 0.9300 | 0.9873 | 0.7537 |
| nest | TypeScript | True | 0.9470 | 0.9776 | 0.0530 | 0.9576 | 0.8865 | 0.9980 | 0.7252 |

Interpretation:
- Internal integrity is strong and stable.
- Strict contract quality is strong overall, with Nest precision/overreach as the weakest strict point.
- Expanded-truth recall drops materially vs strict in all repos, largest in Nest.
- Reasoning reliability remains lower than navigation reliability across all repos.

## 3. Per-Repo Diagnostics

### 3.1 commons_lang (Java)
Strengths:
- Strict recall is very high (0.9904).
- Overreach is low (0.0155).

Weak points:
- Strict method precision/recall: `0.8039 / 0.8119`.
- Navigation reliability is modest (0.8475), driven by module/import precision loss.
- Reasoning reliability is low (0.6571), dominated by method-level mismatch.

### 3.2 fastapi (Python)
Strengths:
- Best strict precision (0.9977) and very low overreach (0.0023).
- Navigation reliability is high (0.9873).

Weak points:
- Method recall remains low: `0.6923`.
- Function recall is moderate: `0.8723`.
- Expanded recall drop (`0.9723 -> 0.9300`) shows missing coverage once non-contract static edges are admitted.

### 3.3 nest (TypeScript)
Strengths:
- Strict recall is high (0.9776).
- Navigation reliability is highest (0.9980).

Weak points:
- Strict precision is lowest of three (0.9470); overreach is highest (0.0530).
- Method precision/recall are weak: `0.7956 / 0.8324`.
- Expanded recall is the lowest overall (0.8865), indicating largest gap to broader static truth.

## 4. SCIONA Core Deficiencies (from regenerated reports)

Priority 1:
- Callable/member resolution quality is the dominant residual core gap.
- Evidence: method-level precision/recall is weakest across all repos; especially Nest and commons_lang.

Priority 2:
- TypeScript strict precision/overreach gap.
- Evidence: Nest strict precision 0.9470 and overreach 0.0530 while recall remains high.

Priority 3:
- Python callable recall gap.
- Evidence: FastAPI method recall 0.6923 and function recall 0.8723 despite near-perfect precision.

What this means:
- Core is contract-consistent and internally correct.
- Remaining issues are analysis power at callable/member resolution depth, not DB/reducer integrity.

## 5. Validation Workflow Deficiencies (from regenerated reports)

Priority 1:
- Expanded truth policy is still coarse.
- Current expanded truth includes all enrichment categories except external; this blends heterogeneous phenomena (dynamic, unresolved, standard-call) into one metric.

Priority 2:
- Prompt reliability is heuristic and not directly tied to downstream task outcomes.
- Useful for ranking risk, but not calibrated against labeled prompt success/failure.

Priority 3:
- Language breakdown is present, but per-kind language detail is still anchored to strict alignment only in markdown summaries.
- Expanded per-kind language detail exists in JSON but is not fully surfaced in report narrative.

Priority 4:
- No confidence slicing inside expanded truth.
- A single expanded score obscures whether gap is from unresolved-name noise vs genuinely useful dynamic/static enrichment.

## 6. Practical Bottom Line
- **Core integrity verdict:** strong.
- **Core quality bottleneck:** method/function resolution (especially TS and PY callables, Java methods).
- **Validation bottleneck:** expanded-truth policy granularity and heuristic prompt-risk interpretation.

For roadmap prioritization:
1. Improve callable/member resolution in core analyzers.
2. Split expanded truth into confidence tiers in validation.
3. Keep strict contract metrics as primary quality gate; keep expanded/prompt metrics diagnostic.
