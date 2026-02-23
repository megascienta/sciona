# Consolidated Reducer Validation Report

Date: 2026-02-23
Sources:
- `experiments/reducers/reports/OpenLineage_reducer_validation.json`
- `experiments/reducers/reports/commons_lang_reducer_validation.json`
- `experiments/reducers/reports/fastapi_reducer_validation.json`
- `experiments/reducers/reports/nest_reducer_validation.json`

## Executive Verdict
All repositories pass hard invariants and internal projection exactness:
- `invariants.hard_passed = true` for all four reports
- `internal_integrity.projection.reducer_db_exact = true`
- `internal_integrity.projection.static_projection_precision = 1.0`
- `internal_integrity.projection.static_projection_recall = 1.0`

This confirms reducer/DB integrity is stable. Remaining gaps are analysis-quality gaps (mostly callable/member resolution), not internal contract integrity failures.

## Cross-Repo Snapshot

| Repo | Hard Passed | Strict Precision | Strict Recall | Overreach | Expanded Full Precision | Expanded Full Recall | Navigation Reliability | Reasoning Reliability | Diagnostic Failures |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| OpenLineage | True | 0.8740 | 0.9490 | 0.1260 | 0.8779 | 0.8877 | 0.8889 | 0.4310 | member-call recall quality gate failed |
| commons_lang | True | 0.9845 | 0.9904 | 0.0155 | 0.9849 | 0.9707 | 0.8475 | 0.6571 | none |
| fastapi | True | 0.9977 | 0.9723 | 0.0023 | 0.9977 | 0.9452 | 0.9873 | 0.7537 | none |
| nest | True | 0.9470 | 0.9776 | 0.0530 | 0.9560 | 0.9113 | 0.9980 | 0.7252 | none |

## What Improved / What Remains
- Workflow-level contract checks are consistently passing across repos.
- Strict-vs-expanded separation is now explicit and policy-scoped (external + standard excluded).
- Largest residual quality loss is still at method/function layer, visible in every repo.

## Repository Diagnostics

### OpenLineage (mixed language)
- Highest risk profile.
- Function: `P/R = 0.458 / 0.803`
- Method: `P/R = 0.561 / 0.717`
- Only repo with an active diagnostic failure (`member-call recall quality gate failed`).
- Interpretation: mixed-language callable resolution is the main bottleneck.

### commons_lang (Java)
- Strong global strict metrics.
- Method remains weaker than module/class/function:
  - Method `P/R = 0.804 / 0.812`
- Interpretation: class/method resolution depth still limits Java callable fidelity.

### fastapi (Python)
- Best precision and lowest overreach.
- Recall gap is concentrated in callable layer:
  - Function recall `0.872`
  - Method recall `0.692`
- Interpretation: static modeling misses some Python callable/member relations.

### nest (TypeScript)
- Strong recall and navigation reliability.
- Precision deficit remains method-heavy:
  - Method `P/R = 0.796 / 0.832`
  - Overreach `0.053`
- Interpretation: TypeScript resolver precision (overresolution) remains the key quality limiter.

## SCIONA Core Deficiencies (Evidence-Backed)
1. Callable/member resolution quality is uneven and is the dominant accuracy limiter.
2. Method precision/recall is the weakest layer in all repos.
3. Mixed-language repositories amplify callable-resolution errors.
4. TypeScript precision control is still weaker than Python/Java on comparable strict metrics.

## Validation Workflow Deficiencies (MUST FIX Only)
1. Consolidated report generation is still manual and drift-prone.
- Risk: markdown can diverge from JSON truth after regeneration.
- Must fix: auto-generate consolidated tables and key claims directly from JSON fields.

No other workflow issue is currently MUST-FIX for correctness:
- hard gates are passing,
- scope policy is explicit,
- strict/enriched separation is functioning as designed.

## Priority Actions
1. Improve core callable/member resolution (all languages).
2. Prioritize TypeScript precision controls and method disambiguation.
3. Add automated consolidated-report generator to remove manual interpretation drift.

## Bottom Line
- Internal correctness (reducer vs DB) is stable and production-grade in these runs.
- Main remaining limitations are core static-analysis coverage/precision at callable/member granularity.
- Validation workflow is structurally sound; only consolidation automation is MUST-FIX.
