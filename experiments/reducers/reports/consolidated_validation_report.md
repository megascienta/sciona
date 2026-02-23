# Consolidated Reducer Validation Report (Critical Consolidation)

Date: 2026-02-23
Sources:
- `experiments/reducers/reports/OpenLineage_reducer_validation.json`
- `experiments/reducers/reports/commons_lang_reducer_validation.json`
- `experiments/reducers/reports/fastapi_reducer_validation.json`
- `experiments/reducers/reports/nest_reducer_validation.json`

## Executive Verdict
- Integrity status is strong: all repos pass hard gates (`hard_passed=true`) and reducer-vs-DB projection remains exact.
- Remaining gaps are quality gaps, not pipeline integrity defects.
- Gap concentration is still call resolution under strict contract constraints, especially member/method resolution.

## Cross-Repo Snapshot (Corrected)
| Repo | Hard Passed | Strict Precision | Strict Recall | Overreach | Expanded Full Precision | Expanded Full Recall | Diagnostic Failures |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| OpenLineage | True | 0.979646 | 0.884185 | 0.020354 | 0.979646 | 0.830458 | contract recall gate, member-call recall gate |
| commons_lang | True | 0.973542 | 0.985034 | 0.026458 | 0.973542 | 0.973339 | none |
| fastapi | True | 0.979132 | 0.984766 | 0.020868 | 0.979132 | 0.964203 | member-call recall gate |
| nest | True | 0.961032 | 0.935826 | 0.038968 | 0.962751 | 0.870016 | contract recall gate, member-call recall gate |

## Critical Findings

### 1) Member-call recall remains the most persistent weakness
- OpenLineage: member recall `0.664474`
- fastapi: member recall `0.666667`
- nest: member recall `0.671296`
- commons_lang: n/a for member-call gate (no sampled member-call denominator in this run)

Interpretation:
- Recent resolver hardening improved contract safety, but member dispatch remains under-resolved under strict acceptance rules.
- This is still the main blocker for repos failing member-call quality gates.

### 2) Method quality remains unstable across repos (precision/recall imbalance)
- OpenLineage method P/R: `0.939759 / 0.600000` (recall drag)
- commons_lang method P/R: `0.318182 / 0.392523` (both weak)
- fastapi method P/R: `0.270833 / 0.812500` (severe over-resolution/precision collapse)
- nest method P/R: `0.962025 / 0.684685` (recall drag)

Interpretation:
- The same architecture shows opposite failure modes by codebase: over-conservative in some contexts (FN-heavy), over-aggressive in others (FP-heavy).
- This indicates calibration and stage-priority issues in deterministic resolver heuristics, not one simple global threshold issue.

### 3) Strict-to-expanded recall drop is still material where unresolved/dynamic calls are high
- OpenLineage strict->expanded recall delta: `-0.0537277`
- commons_lang delta: `-0.0116955`
- fastapi delta: `-0.0205625`
- nest delta: `-0.0658104`

Interpretation:
- Nest and OpenLineage remain most sensitive to unresolved/dynamic limitations.
- This still limits reasoning reliability even when strict contract metrics are acceptable.

### 4) Import precision is still noisy in Java-heavy repos
- OpenLineage imports P/R: `0.820896 / 0.982143`
- commons_lang imports P/R: `0.831818 / 1.000000`
- fastapi imports P/R: `0.997814 / 0.992032`
- nest imports P/R: `0.997992 / 1.000000`

Interpretation:
- Import FP remains a Java-heavy pain point; Python/TypeScript import normalization looks substantially better in these runs.

### 5) Resolver diagnostics show ambiguity + missing-candidate pressure is still high
Aggregate across all 4 repos:
- Accepted by provenance: `exact_qname=803`, `import_narrowed=47`, `module_scoped=5`
- Dropped by reason: `no_candidates=204`, `unique_without_provenance=102`, `ambiguous_no_in_scope_candidate=140`, `ambiguous_multiple_in_scope_candidates=15`

Interpretation:
- Precision-first provenance gating is working as intended.
- Recall ceilings are now dominated by deterministic ambiguity and missing-candidate generation, not post-filter acceptance logic.

### 6) Mismatch attribution remains large in both directions
Aggregate mismatch counts:
- `core_overresolution=3907`
- `independent_overprojection=3995`
- `core_missed_resolution=0`
- `normalization_contract_mismatch=0`

Interpretation:
- Large bi-directional disagreement persists between core and independent truth proxies.
- The zero normalization mismatch is positive; disagreement is mostly about resolution semantics/coverage rather than identifier canonicalization bugs.

### 7) Class mapping reliability metric is now explicit and currently healthy
- All four repos report `class_rows_unreliable_mapping=0` and `unreliable_mapping_rate=0.0`.
- The previous blind-spot risk from silent exclusions is currently not observed in these sampled runs.

## Remaining Problems (Prioritized)

### P0: Member/method call resolution parity is not yet good enough
Symptoms:
- Repeated member-call recall failures.
- Large method quality variance by repo.

Impact:
- Primary source of strict-recall misses and reasoning-quality volatility.

### P1: Java import precision remains low in mixed/large repos
Symptoms:
- Import precision around `0.82-0.83` in OpenLineage/commons_lang.

Impact:
- FP pressure in strict contract alignment despite good recall.

### P1: Resolver ambiguity pressure is still high
Symptoms:
- `ambiguous_*` + `no_candidates` + `unique_without_provenance` drops remain substantial.

Impact:
- Hard upper bound on recall without improving deterministic pre-fallback binding.

### P2: Expanded-truth robustness still trails strict truth in dynamic/unresolved-heavy repos
Symptoms:
- Larger strict->expanded recall drops in Nest and OpenLineage.

Impact:
- Practical reasoning reliability remains below target even when strict pass conditions hold.

## Recommended Next Work (ROI-Oriented)

### High ROI
1. Deepen deterministic receiver/type binding for member calls before fallback (language-specific).
- Focus: multi-hop receiver chains, constructor/field binding propagation, alias-aware import narrowing.
- Expected: largest gain on member/method recall with controlled precision.

2. Add targeted fixture families tied to observed drops (`no_candidates`, `ambiguous_no_in_scope_candidate`, `unique_without_provenance`).
- Focus: Java import-heavy ambiguity, Python service chaining, TS DI/member chains.
- Expected: faster iteration and measurable reduction in specific dropped-reason buckets.

3. Add repo-level regression gates on dropped-reason budgets (not only aggregate recall/precision).
- Focus: fail when ambiguity/no-candidate counts regress materially.
- Expected: protects against silent quality regression hidden by pass/fail headlines.

### Medium ROI
1. Tighten Java import canonicalization and in-module scope narrowing heuristics.
- Expected: reduce import FP in Java-heavy repos.

2. Surface per-language method/member calibration profiles in report.
- Expected: makes cross-repo overfit/underfit visible and shortens tuning cycles.

3. Add explicit confidence buckets in report text for independent truth interpretation.
- Expected: better communication and fewer false assumptions that proxy truth is absolute.

## Bottom Line
- The architecture is now contract-safe and observably deterministic.
- The remaining performance ceiling is mostly a deterministic call-resolution depth problem, concentrated in member/method resolution and Java import precision.
- Next wins will come from language-specific resolver depth plus fixture-driven ambiguity reduction, not from relaxing contract strictness.
