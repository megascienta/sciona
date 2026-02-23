# Consolidated Reducer Validation Report (Aggressive Revision)

Date: 2026-02-23
Source-of-truth artifacts:
- `experiments/reducers/reports/OpenLineage_reducer_validation.json`
- `experiments/reducers/reports/commons_lang_reducer_validation.json`
- `experiments/reducers/reports/fastapi_reducer_validation.json`
- `experiments/reducers/reports/nest_reducer_validation.json`

## 1. Executive Verdict
- All four runs pass hard integrity gates (`invariants.hard_passed = true`).
- All four runs have exact reducer<->DB projection (`reducer_db_exact = true`, precision=1.0, recall=1.0).
- Therefore: non-100% alignment is **not** a reducer materialization integrity bug; it is predominantly a **call/import resolution quality** gap against the independent strict proxy truth.

## 2. Corrected Cross-Repo Snapshot

| Repo | Hard Passed | Strict Precision | Strict Recall | Overreach | Expanded Full Precision | Expanded Full Recall | Diagnostic Failures |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| OpenLineage | True | 0.9676 | 0.8991 | 0.0324 | 0.9700 | 0.8556 | contract recall gate; member-call recall gate |
| commons_lang | True | 0.9804 | 0.9729 | 0.0196 | 0.9806 | 0.9609 | none |
| fastapi | True | 0.9643 | 0.9792 | 0.0357 | 0.9643 | 0.9617 | member-call recall gate |
| nest | True | 0.9380 | 0.9416 | 0.0620 | 0.9391 | 0.8870 | contract recall gate; member-call recall gate |

## 3. Where Errors Actually Concentrate

### 3.1 By edge type (strict)
| Repo | Calls P/R | Imports P/R | Key concentration |
| --- | --- | --- | --- |
| OpenLineage | 0.9753 / 0.8926 | 0.8812 / 0.9889 | Imports precision + call recall |
| commons_lang | 0.9888 / 0.9717 | 0.8252 / 1.0000 | Imports precision dominates FP |
| fastapi | 0.6383 / 0.8219 | 0.9978 / 0.9917 | Call precision dominates FP |
| nest | 0.9116 / 0.9161 | 0.9982 / 1.0000 | Calls dominate both FP/FN |

### 3.2 By callable kind (strict)
| Repo | Function P/R | Method P/R | Member-call recall |
| --- | --- | --- | --- |
| OpenLineage | 0.9189 / 0.6667 | 0.8791 / 0.6178 | 0.7013 |
| commons_lang | n/a | 0.6531 / 0.4344 | n/a |
| fastapi | 0.5726 / 0.6768 | 0.2353 / 0.6957 | 0.4615 |
| nest | 0.9244 / 0.6875 | 0.5603 / 0.6077 | 0.5985 |

Conclusion: **method/member resolution is the most persistent weakness across repos**. FastAPI has extreme method precision loss; Nest has method dual loss; OpenLineage has mixed-language recall drag.

## 4. Main Drivers Of Non-100% Strict Alignment

### Driver A: shallow deterministic adapter heuristics (core)
Evidence:
- Python resolver is mostly alias/instance/self/module heuristics, first-match return: `src/sciona/code_analysis/core/extract/languages/python_calls.py:70`.
- TypeScript resolver similarly relies on alias/class/instance shortcuts with early return: `src/sciona/code_analysis/core/extract/languages/typescript_calls.py:65`.
- Java resolver relies on simple receiver-type/import-class heuristics and unique-class fallback: `src/sciona/code_analysis/core/extract/languages/java_calls.py:85`.
Impact pattern:
- Lower method/member recall (FN) from conservative abstention.
- Lower precision (FP), especially where aliases/terminals overfit (`fastapi` method precision 0.2353).

### Driver B: terminal fallback in shared kernel + later symbol narrowing (core)
Evidence:
- Kernel fallback emits unresolved terminal when adapter has no candidate: `src/sciona/code_analysis/core/extract/languages/call_resolution_kernel.py:39`.
- Rollup resolution later tries terminal/full-name matching and provenance narrowing: `src/sciona/code_analysis/artifacts/rollups.py:243`.
- Symbol index intentionally stores both terminals and full qnames, increasing collision surface: `src/sciona/code_analysis/artifacts/rollups.py:189`.
Impact pattern:
- Potential FP pressure from terminal collisions when identifier is weak.
- Potential FN pressure from strict provenance drops (`unique_without_provenance`, ambiguity drops).

### Driver C: strict provenance gate intentionally drops uncertain candidates (core)
Evidence:
- `_resolve_callees` only accepts exact-qname/module-scoped/import-narrowed certainty and drops ambiguous/weakly-provenanced candidates: `src/sciona/code_analysis/artifacts/rollups.py:270`.
- `write_call_artifacts` skips records when no resolved callees survive: `src/sciona/code_analysis/artifacts/rollups.py:160`.
Impact pattern:
- Contract safety improves, but recall decreases in high-ambiguity/member-heavy code.

### Driver D: independent strict proxy still uses deterministic heuristics (validation side)
Evidence:
- Contract truth resolution uses multi-stage heuristic resolution (`receiver_bindings`, module symbol index, import hints, namespace aliases): `experiments/reducers/validation/call_contract.py:92`.
- Class truth mapping can use non-exact fallback strategies (`simple_unique`, `parent_and_simple`, `line_span_overlap`) and marks unreliable when unmatched: `experiments/reducers/validation/ground_truth.py:199`.
- Evaluation suppresses class rows marked unreliable from contract/enriched scoring: `experiments/reducers/validation/evaluation.py:536`.
Impact pattern:
- Strict proxy truth is deterministic and useful, but not absolute.
- Some residual mismatch is expected from proxy-vs-proxy modeling differences.

### Driver E: import normalization/resolution asymmetry in some repos
Evidence:
- `commons_lang` import precision is 0.8252 with recall 1.0, indicating over-resolution FP concentration in imports.
Impact pattern:
- Repo/language-specific import canonicalization differences can dominate strict FP even when call resolution is strong.

## 5. Priority Interpretation (ROI)

### High ROI (major influence)
1. Improve method/member resolution depth in language adapters (`*_calls.py`) while preserving deterministic abstention on true ambiguity.
- Why ROI is high: method/member is weakest axis in every repo.
- Expected effect: biggest recall and precision gain on strict calls metrics.

2. Add mandatory rollup diagnostics reporting in validation outputs (accepted provenance + dropped reasons histogram).
- Why ROI is high: fast root-cause visibility for FP/FN; shortens iteration loop.
- Expected effect: faster targeted fixes, less blind tuning.

### Medium ROI
3. Tighten terminal fallback acceptance path by requiring stronger provenance before terminal-derived acceptance.
- Why ROI is medium: can reduce FP in ambiguous terminal collisions; may reduce recall if too strict.

4. Repo/language fixture expansion for known hard patterns (aliases, chained receivers, namespace imports, constructor/member dispatch) with differential checks.
- Why ROI is medium: catches regressions and quantifies progress; slower to create but durable.

### Lower ROI (for strict-alignment headline)
5. Further polishing of global aggregate reliability metrics language.
- Useful for communication clarity, but does not materially improve strict alignment itself.

## 6. Bottom Line
- Contract integrity is solid; reducer<->DB is exact.
- Non-100% strict alignment is mainly a **resolution quality frontier**, not a data integrity defect.
- The most leverage is in **method/member resolver depth + diagnostics-driven iteration**, not in relaxing contract constraints.
