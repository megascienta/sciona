# SCIONA Reducer Validation Report

## Executive Summary

- repo=fastapi
- sampled_nodes=500
- invariants_passed=True

## Run Verdict

- passed: `True`
- hard_passed: `True`
- threshold_profile: `single_language`
- gate_reducer_db_exact: `True`
- gate_aligned_scoring: `True`
- gate_parse_coverage: `True`
- gate_contract_truth_pure: `True`
- gate_contract_truth_resolved: `True`
- gate_parser_deterministic: `True`
- gate_no_duplicate_contract_edges: `True`
- gate_typescript_relative_index_contract: `True`
- gate_class_truth_nonempty_rate: `True`
- gate_class_truth_match_rate: `True`
- gate_scoped_call_normalization: `True`
- gate_contract_recall_min: `True`
- gate_overreach_rate_max: `True`
- gate_member_call_recall_min: `True`
- gate_equal_contract_metrics_when_exact: `True`

## Internal Integrity (Hard Gates)

- valid: `True`
- static_projection_precision: `1.000000`
- static_projection_recall: `1.000000`
- parser_stability_score: `1.000000`

## Contract Alignment (Strict)

- static_contract_precision: `0.997686`
- static_contract_recall: `0.972294`
- static_overreach_rate: `0.002314`
- static_divergence_index: `0.029894`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.996265172735761, 1.0], 'recall_ci95': [0.8804347826086957, 0.9846640316205534], 'n': 500}, 'method': {'precision_ci95': [1.0, 1.0], 'recall_ci95': [0.6050420168067226, 0.7692307692307693], 'n': 125}}`

## Expanded Truth Alignment (Diagnostic)

- reducer_vs_enriched_truth_precision: `0.997686`
- reducer_vs_enriched_truth_recall: `0.945193`
- db_vs_enriched_truth_precision: `0.997686`
- db_vs_enriched_truth_recall: `0.945193`
- reducer_vs_enriched_truth_divergence_index: `0.056875`
- inclusion_policy: `{'base': 'contract_truth_edges + limitation_edges', 'scope_exclusions': ['standard_call', 'external'], 'limitation_focus': ['dynamic', 'in_repo_unresolved', 'relative_unresolved'], 'confidence_tiers': {'high': ['in_repo_unresolved'], 'low': ['dynamic', 'relative_unresolved']}, 'notes': 'Expanded truth is diagnostic-only and non-gating.'}`
- tier.high_conf: reducer_p/r=`0.997686`/`0.948460`, db_p/r=`0.997686`/`0.948460`, divergence=`0.053622`
- tier.full: reducer_p/r=`0.997686`/`0.945193`, db_p/r=`0.997686`/`0.945193`, divergence=`0.056875`
- tier_edge_counts: `{'high_conf_edges': 3182, 'full_edges': 3193}`
- scope_split_counts: `{'excluded_out_of_scope_edges': 5623, 'included_limitation_edges': 120, 'excluded_out_of_scope_by_reason': {'external': 5539, 'standard_call': 84}, 'included_limitation_by_reason': {'relative_unresolved': 6, 'in_repo_unresolved': 101, 'dynamic': 13}}`
Reason-level expanded recall:
- reason.dynamic: reducer_recall=`0.000000`, db_recall=`0.000000`, reducer_tp/fn=`0/7`
- reason.in_repo_unresolved: reducer_recall=`0.000000`, db_recall=`0.000000`, reducer_tp/fn=`0/78`
- reason.relative_unresolved: reducer_recall=`0.000000`, db_recall=`0.000000`, reducer_tp/fn=`0/4`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.9954614220877458, 1.0], 'recall_ci95': [0.7649918962722853, 0.9715515915731201], 'n': 500}}`

## Prompt Reliability (Heuristic Diagnostics)

- navigation_structural_reliability: `0.987300`
- reasoning_structural_reliability: `0.753715`
- coupling_stability_index: `0.997686`
- prompt_reliability_version: `v1`
- weights: `{'navigation': {'fp_weight': 1.0, 'fn_weight': 1.0}, 'reasoning': {'fp_weight': 1.0, 'fn_weight': 1.2}}`
- component_contributions: `{'navigation': {'tp': 2721, 'fp': 7, 'fn': 28, 'penalty_fp': 7.0, 'penalty_fn': 28.0, 'denominator': 2756.0}, 'reasoning': {'tp': 213, 'fp': 0, 'fn': 58, 'penalty_fp': 0.0, 'penalty_fn': 69.6, 'denominator': 282.6}}`
- enrichment_noise_ratio: `0.027873`

## Language Breakdown

- python: sampled_nodes=`500`, population_nodes=`6363`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`0.997686`/`0.972294`, expanded_p/r=`0.997686`/`0.945193`, contract_overreach=`0.002314`, projection_tp/fp/fn=`3025/0/0`, contract_tp/fp/fn=`3018/7/86`
- python:module: recall=`0.989814`, precision=`0.997434`, tp/fp/fn=`2721/7/28`
- python:class: recall=`1.000000`, precision=`1.000000`, tp/fp/fn=`84/0/0`
- python:function: recall=`0.872340`, precision=`1.000000`, tp/fp/fn=`123/0/18`
- python:method: recall=`0.692308`, precision=`1.000000`, tp/fp/fn=`90/0/40`

Expanded Alignment by language:kind
- python:module: strict_p/r=`0.997434`/`0.989814`, expanded_p/r=`0.997434`/`0.988017`
- python:class: strict_p/r=`1.000000`/`1.000000`, expanded_p/r=`1.000000`/`1.000000`
- python:function: strict_p/r=`1.000000`/`0.872340`, expanded_p/r=`1.000000`/`0.582938`
- python:method: strict_p/r=`1.000000`/`0.692308`, expanded_p/r=`1.000000`/`0.625000`

Strict vs Expanded delta by kind (top-5 worst recall delta)
- python:function: delta_recall=`0.289402`, delta_precision=`0.000000`
- python:method: delta_recall=`0.067308`, delta_precision=`0.000000`
- python:module: delta_recall=`0.001797`, delta_precision=`0.000000`
- python:class: delta_recall=`0.000000`, delta_precision=`0.000000`

## Call Resolution Diagnostics

- call_form.direct: tp=`2916`, fn=`64`, recall=`0.978523`
- call_form.member: tp=`106`, fn=`18`, recall=`0.854839`
- mismatch_attribution.core_missed_resolution: `0`
- mismatch_attribution.core_overresolution: `19`
- mismatch_attribution.normalization_contract_mismatch: `0`
- mismatch_attribution.independent_overprojection: `94`

## Out-of-Contract Distribution

- call: `113`
- import: `7`

Breakdown by `edge_type::language::reason`:
- call::python::dynamic: `13`
- call::python::in_repo_unresolved: `100`
- import::python::in_repo_unresolved: `1`
- import::python::relative_unresolved: `6`

Note: `enrichment_edges` includes only in-repo out-of-contract edges (unresolved, dynamic, standard-call filtered); external edges are excluded.

## Independent Parser Coverage & Totals

- coverage.python: files_parsed/files_total=`1284/1284` (1.000000)
- raw_call_edges: `15400`
- raw_import_edges: `4856`
- normalized_call_edges: `15400`
- normalized_import_edges: `4856`
- contract_truth_edges: `3104`
- enrichment_edges: `89`
- enriched_truth_edges: `3193`
- expanded_high_conf_edges: `3182`
- expanded_full_edges: `3193`
- excluded_out_of_scope_edges: `5623`
- included_limitation_edges: `120`

## Core Metrics

- static_contract_recall: `0.972294`
- static_overreach_rate: `0.002314`
- overreach_count: `7`
- reducer_edge_total: `3025`

## Action Priority Board

- [high] core_analysis::method_recall_gap evidence=`{'method_recall': 0.6923076923076923}`
- [medium] core_analysis::function_recall_gap evidence=`{'function_recall': 0.8723404255319149}`

## Metric Definitions & Schema

- report_schema_version: `2026-02-23`
- enriched_alignment_precision: layer=`enrichment_practical`, source=`reducer_vs_enriched_truth`, formula=`tp / (tp + fp)`
- enriched_alignment_recall: layer=`enrichment_practical`, source=`reducer_vs_enriched_truth`, formula=`tp / (tp + fn)`
- expanded_full_precision: layer=`enrichment_practical`, source=`reducer_vs_expanded_full`, formula=`tp / (tp + fp)`
- expanded_full_recall: layer=`enrichment_practical`, source=`reducer_vs_expanded_full`, formula=`tp / (tp + fn)`
- expanded_high_conf_precision: layer=`enrichment_practical`, source=`reducer_vs_expanded_high_conf`, formula=`tp / (tp + fp)`
- expanded_high_conf_recall: layer=`enrichment_practical`, source=`reducer_vs_expanded_high_conf`, formula=`tp / (tp + fn)`
- static_contract_precision: layer=`static_contract_alignment`, source=`reducer_vs_contract_truth`, formula=`tp / (tp + fp)`
- static_contract_recall: layer=`static_contract_alignment`, source=`reducer_vs_contract_truth`, formula=`tp / (tp + fn)`
- static_overreach_rate: layer=`static_contract_alignment`, source=`reducer_vs_contract_truth`, formula=`fp / (tp + fp)`
- static_projection_precision: layer=`internal_integrity`, source=`reducer_vs_db`, formula=`tp / (tp + fp)`
- static_projection_recall: layer=`internal_integrity`, source=`reducer_vs_db`, formula=`tp / (tp + fn)`

