# SCIONA Reducer Validation Report

## Executive Summary

- repo=fastapi
- sampled_nodes=500
- invariants_passed=True
- interpretation_note: independent truth is a deterministic static proxy, not absolute ground truth.

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
- gate_strict_contract_parity: `True`
- gate_contract_recall_min: `True`
- gate_overreach_rate_max: `True`
- gate_member_call_recall_min: `True`
- gate_equal_contract_metrics_when_exact: `True`

## Internal Integrity (Hard Gates)

- valid: `True`
- static_projection_precision: `1.000000`
- static_projection_recall: `1.000000`
- parser_stability_score: `1.000000`

## Strict Contract Alignment (Gating)

- static_contract_precision: `0.979132`
- static_contract_recall: `0.992494`
- static_overreach_rate: `0.020868`
- static_divergence_index: `0.028065`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.8661417322834646, 0.9901441868954188], 'recall_ci95': [0.9768421052631578, 0.997134670487106], 'n': 500}, 'method': {'precision_ci95': [0.125, 0.4222222222222222], 'recall_ci95': [1.0, 1.0], 'n': 125}}`

## Enrichment Alignment (Non-Gating Diagnostics)

- reducer_vs_enriched_truth_precision: `0.979132`
- reducer_vs_enriched_truth_recall: `0.964203`
- db_vs_enriched_truth_precision: `0.979132`
- db_vs_enriched_truth_recall: `0.964203`
- reducer_vs_enriched_truth_divergence_index: `0.055213`
- inclusion_policy: `{'base': 'contract_truth_edges + limitation_edges', 'scope_exclusions': ['standard_call', 'external'], 'limitation_focus': ['dynamic', 'in_repo_unresolved', 'relative_unresolved'], 'confidence_tiers': {'high': ['in_repo_unresolved'], 'low': ['dynamic', 'relative_unresolved']}, 'notes': 'Expanded truth is diagnostic-only and non-gating.'}`
- tier.high_conf: reducer_p/r=`0.979132`/`0.966766`, db_p/r=`0.979132`/`0.966766`, divergence=`0.052752`
- tier.full: reducer_p/r=`0.979132`/`0.964203`, db_p/r=`0.979132`/`0.964203`, divergence=`0.055213`
- tier_edge_counts: `{'high_conf_edges': 3009, 'full_edges': 3017}`
- scope_split_counts: `{'excluded_out_of_scope_edges': 4711, 'included_limitation_edges': 96, 'excluded_out_of_scope_by_reason': {'external': 4691, 'standard_call': 20}, 'included_limitation_by_reason': {'in_repo_unresolved': 83, 'dynamic': 7, 'relative_unresolved': 6}}`
Reason-level expanded proxy recall:
- reason.dynamic: reducer_recall=`0.000000`, db_recall=`0.000000`, reducer_tp/fn=`0/4`
- reason.in_repo_unresolved: reducer_recall=`0.000000`, db_recall=`0.000000`, reducer_tp/fn=`0/78`
- reason.relative_unresolved: reducer_recall=`0.000000`, db_recall=`0.000000`, reducer_tp/fn=`0/4`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.8774703557312253, 0.9898385048085647], 'recall_ci95': [0.8078175895765473, 0.9799787007454739], 'n': 500}}`

## Enrichment Reliability (Heuristic)

- navigation_structural_reliability: `0.989881`
- reasoning_structural_reliability: `0.605634`
- coupling_stability_index: `0.979132`
- prompt_reliability_version: `v1`
- weights: `{'navigation': {'fp_weight': 1.0, 'fn_weight': 1.0}, 'reasoning': {'fp_weight': 1.0, 'fn_weight': 1.2}}`
- component_contributions: `{'navigation': {'tp': 2739, 'fp': 6, 'fn': 22, 'penalty_fp': 6.0, 'penalty_fn': 22.0, 'denominator': 2767.0}, 'reasoning': {'tp': 86, 'fp': 56, 'fn': 0, 'penalty_fp': 56.0, 'penalty_fn': 0.0, 'denominator': 142.0}}`
- enrichment_noise_ratio: `0.028505`

## Language Breakdown

- python: sampled_nodes=`500`, population_nodes=`6363`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`0.979132`/`0.992494`, expanded_p/r=`0.979132`/`0.964203`, contract_overreach=`0.020868`, projection_tp/fp/fn=`2971/0/0`, contract_tp/fp/fn=`2909/62/22`
- python:module: recall=`0.992032`, precision=`0.997814`, tp/fp/fn=`2739/6/22`
- python:class: recall=`1.000000`, precision=`1.000000`, tp/fp/fn=`84/0/0`
- python:function: recall=`1.000000`, precision=`0.776596`, tp/fp/fn=`73/21/0`
- python:method: recall=`1.000000`, precision=`0.270833`, tp/fp/fn=`13/35/0`

Expanded Proxy Alignment by language:kind
- python:module: strict_p/r=`0.997814`/`0.992032`, expanded_p/r=`0.997814`/`0.990239`
- python:class: strict_p/r=`1.000000`/`1.000000`, expanded_p/r=`1.000000`/`1.000000`
- python:function: strict_p/r=`0.776596`/`1.000000`, expanded_p/r=`0.776596`/`0.500000`
- python:method: strict_p/r=`0.270833`/`1.000000`, expanded_p/r=`0.270833`/`0.619048`

Strict vs Expanded delta by kind (top-5 worst recall delta)
- python:function: delta_recall=`0.500000`, delta_precision=`0.000000`
- python:method: delta_recall=`0.380952`, delta_precision=`0.000000`
- python:module: delta_recall=`0.001793`, delta_precision=`0.000000`
- python:class: delta_recall=`0.000000`, delta_precision=`0.000000`

## Independent Strict Contract Diagnostics

- strict_contract.accepted_by_provenance: `{'import_narrowed': 39, 'module_scoped': 80}`
- strict_contract.dropped_by_reason: `{'unique_without_provenance': 46, 'no_candidates': 164, 'ambiguous_no_in_scope_candidate': 59, 'ambiguous_multiple_in_scope_candidates': 1}`
- strict_contract.candidate_count_histogram: `{'1': 126, '4': 12, '0': 164, '3': 11, '9': 34, '2': 35, '134': 2, '14': 3, '6': 2}`

## Call Resolution Diagnostics

- call_form.direct: tp=`2895`, fn=`22`, recall=`0.992458`
- call_form.member: tp=`14`, fn=`0`, recall=`1.000000`
- mismatch_attribution.core_missed_resolution: `0`
- mismatch_attribution.core_overresolution: `128`
- mismatch_attribution.normalization_contract_mismatch: `0`
- mismatch_attribution.independent_overprojection: `88`
- resolution.accepted_by_provenance: `{'exact_qname': 142}`
- resolution.dropped_by_reason: `{'no_candidates': 5}`
- resolution.candidate_count_histogram: `{'1': 142, '0': 5}`
- resolution.record_drops: `{'no_resolved_callees': 2}`
- resolution.python:function: accepted=`{'exact_qname': 94}`, dropped=`{'no_candidates': 3}`
- resolution.python:method: accepted=`{'exact_qname': 48}`, dropped=`{'no_candidates': 2}`

## Class Mapping Reliability

- class_rows_parse_ok_with_methods: `27`
- class_rows_unreliable_mapping: `0`
- class_rows_scored: `27`
- unreliable_mapping_rate: `0.000000`

## Out-of-Contract Distribution

- call: `89`
- import: `7`

Breakdown by `edge_type::language::reason`:
- call::python::dynamic: `7`
- call::python::in_repo_unresolved: `82`
- import::python::in_repo_unresolved: `1`
- import::python::relative_unresolved: `6`

Note: `enrichment_edges` includes only in-repo out-of-contract edges (unresolved, dynamic, standard-call filtered); external edges are excluded.

## Independent Parser Coverage & Totals

- coverage.python: files_parsed/files_total=`1284/1284` (1.000000)
- raw_call_edges: `15400`
- raw_import_edges: `4856`
- normalized_call_edges: `15400`
- normalized_import_edges: `4856`
- contract_truth_edges: `2931`
- enrichment_edges: `86`
- enriched_truth_edges: `3017`
- expanded_high_conf_edges: `3009`
- expanded_full_edges: `3017`
- excluded_out_of_scope_edges: `4711`
- included_limitation_edges: `96`

## Core Metrics

- static_contract_recall: `0.992494`
- static_overreach_rate: `0.020868`
- overreach_count: `62`
- reducer_edge_total: `2971`

## Action Priority Board

- [high] core_analysis::method_precision_gap evidence=`{'method_precision': 0.2708333333333333}`
- [medium] core_analysis::reasoning_reliability_low evidence=`{'reasoning_structural_reliability': 0.6056338028169014}`

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

