# Reducer Validation Workflow (Current)

## 1. Purpose
Validation has two primary goals:
- prove reducer-to-DB internal integrity,
- measure reducer alignment against independent parser proxy truth.

Evaluated relation scope:
- module imports,
- class-defined methods,
- callable neighbors.

## 2. Independence Boundary
Required:
- parser/normalization/call-resolution truth logic lives in `validations/reducers/validation/independent/*` and validation modules,
- no semantic reuse from SCIONA core language analyzers.
- strict contract acceptance is shared and canonicalized via `src/sciona/code_analysis/contracts/strict_call_contract.py` (required parity path).

Allowed shared utilities:
- runtime/config/path helpers,
- reducer/DB adapters,
- generic dataclasses.

## 3. Truth Channels

### 3.1 Strict Contract Truth (Gating)
- in-repo resolvable edges only,
- candidate-only independent evidence is accepted/rejected through shared strict contract rules,
- used for primary static contract alignment scoring.

### 3.2 Limitation-Focused Enrichment Truth (Non-Gating)
Built from strict proxy truth plus selected in-repo limitation edges.

Policy (authoritative via code configuration):
- `validations/reducers/validation/contract_spec.py` (validation contract policy surface)
- `validations/reducers/validation/config.py` (thresholds and expanded-truth policy)
- `scope_exclusions`: `standard_call`, `external`
- `limitation_focus`: `dynamic`, `in_repo_unresolved`, `relative_unresolved`

Confidence tiers:
- high: `in_repo_unresolved`
- low: `dynamic`, `relative_unresolved`
- full expanded: high + low

Rationale:
- keep applicability-domain mismatch out,
- isolate static-analysis limitation gap.

## 4. Pipeline
1. Load DB population (`module/class/function/method`).
2. Stratified sample by language/kind/size buckets.
3. Parse sampled files with independent parsers (PY/TS/Java).
4. Normalize parser outputs and build independent call-resolution context (candidate production only).
5. Apply shared strict contract selector to independent candidates (`accept_if_single` + provenance rules).
6. Build per-node edge channels:
- `contract_truth_edges`
- `enrichment_edges` (only limitation-focus reasons)
- `expanded_truth_edges_high_conf`
- `expanded_truth_edges_full`
7. Score per node:
- `reducer_vs_db`
- `reducer_vs_contract_truth`
- `db_vs_contract_truth`
- `reducer_vs_expanded_high_conf`
- `reducer_vs_expanded_full`
- `db_vs_expanded_high_conf`
- `db_vs_expanded_full`
8. Evaluate invariants (hard + diagnostic).
9. Emit JSON and markdown reports.

## 5. Report Order
1. Run Verdict
2. Internal Integrity (Hard Gates)
3. Strict Contract Alignment (Gating)
4. Enrichment Alignment (Non-Gating Diagnostics)
5. Enrichment Reliability (Heuristic)
6. Language Breakdown
7. Expanded/Enrichment Alignment by language:kind
8. Strict vs Expanded delta by kind (top-5 worst)
9. Independent Strict Contract Diagnostics
10. Call Resolution Diagnostics
11. Out-of-Contract Distribution
12. Independent Parser Coverage & Totals
13. Core Metrics
14. Metric Definitions & Schema
15. Action Priority Board

## 6. Metric Layers

### 6.1 Internal Integrity (hard-gated)
- reducer↔DB projection precision/recall,
- parser determinism.

### 6.2 Strict Contract Alignment (gating)
- strict precision/recall/overreach/divergence,
- per-kind/edge/call-form diagnostics.
- bootstrap uncertainty intervals (micro + method scope).

### 6.3 Enrichment Alignment (non-gating)
- reducer/db alignment vs expanded proxy truth,
- high/full tier precision/recall/divergence,
- explicit scope policy and counts:
- `excluded_out_of_scope_edges`
- `included_limitation_edges`
- reason-level expanded proxy recall diagnostics (reducer/db).
- bootstrap uncertainty interval for expanded-full micro metrics.

### 6.4 Enrichment Reliability (heuristic diagnostics)
- navigation/reasoning/coupling signals,
- explicit weights and `prompt_reliability_version`,
- component contributions (tp/fp/fn penalties).

## 7. Gates

Hard gates (run validity):
- `gate_reducer_db_exact`
- `gate_aligned_scoring`
- `gate_parse_coverage`
- `gate_contract_truth_pure`
- `gate_contract_truth_resolved`
- `gate_parser_deterministic`
- `gate_no_duplicate_contract_edges`
- `gate_scoped_call_normalization`
- `gate_strict_contract_parity`
- `gate_equal_contract_metrics_when_exact`

Diagnostic gates (non-blocking by default):
- `gate_typescript_relative_index_contract`
- `gate_class_truth_nonempty_rate`
- `gate_class_truth_match_rate`
- `gate_contract_recall_min`
- `gate_overreach_rate_max`
- `gate_member_call_recall_min`

`invariants.passed` / `invariants.hard_passed` reflect hard gates only.

Threshold profile selection is automatic:
- `single_language` profile for one-language samples,
- `multi_language` profile otherwise.
The active profile is emitted as `quality_gates.threshold_profile`.

## 8. Formulas
- precision: `tp / (tp + fp)`
- recall: `tp / (tp + fn)`
- strict overreach: `fp / (tp + fp)` on strict contract comparison
- divergence: `(fp + fn) / (tp + fp + fn)`
- weighted heuristic reliability: `tp / (tp + fp_w*fp + fn_w*fn)`

Canonical metric source/formula mapping is emitted in `metric_definitions`.

## 9. Top-Level JSON Keys
- `report_schema_version`
- `summary`
- `invariants`
- `metric_definitions`
- `core_metrics`
- `internal_integrity`
- `static_contract_alignment`
- `enriched_truth_alignment`
- `enrichment_practical`
- `micro_metrics`
- `micro_metrics_by_kind`
- `micro_metrics_by_language`
- `micro_metrics_by_language_and_kind`
- diagnostics blocks (`call_form_recall`, edge breakdowns, mismatch attribution, out-of-contract)
- `strict_contract_diagnostics`
- parser/stability/population/per-node blocks

## 10. Run
```bash
python validations/reducers/reducer_validation.py \
  --repo-root /path/to/repo \
  --nodes 500 \
  --seed 20260221 \
  --stability-runs 2
```

## 11. Interpretation
1. Run Verdict first.
2. If internal integrity is valid, reducer is faithful DB projection for evaluated nodes.
3. Use strict contract alignment (gating) as primary external quality signal.
4. Use enrichment alignment to quantify static limitation gap only (without standard/external contamination).
5. Use enrichment reliability only as heuristic downstream risk.

## 12. Known Limits
- Independent parsing remains static and cannot model runtime behavior perfectly.
- Independent truth is a deterministic static proxy, not absolute ground truth.
- Expanded proxy truth remains diagnostic; not a correctness gate.
- Java fixture tests require `SCIONA_JAVAPARSER_JAR` + `java/javac`.
