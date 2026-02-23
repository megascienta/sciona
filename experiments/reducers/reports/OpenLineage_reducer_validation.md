# SCIONA Reducer Validation Report

## Executive Summary

- repo=OpenLineage
- sampled_nodes=500
- invariants_passed=True
- interpretation_note: independent truth is a deterministic static proxy, not absolute ground truth.

## Run Verdict

- passed: `True`
- hard_passed: `True`
- threshold_profile: `multi_language`
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
- gate_contract_recall_min: `False`
- gate_overreach_rate_max: `True`
- gate_member_call_recall_min: `False`
- gate_equal_contract_metrics_when_exact: `True`
- diagnostic_failure: contract recall quality gate failed
- diagnostic_failure: member-call recall quality gate failed

## Internal Integrity (Hard Gates)

- valid: `True`
- static_projection_precision: `1.000000`
- static_projection_recall: `1.000000`
- parser_stability_score: `1.000000`

## Contract Alignment (Strict Proxy)

- static_contract_precision: `0.967585`
- static_contract_recall: `0.899096`
- static_overreach_rate: `0.032415`
- static_divergence_index: `0.127193`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.9498207885304659, 0.9784366576819407], 'recall_ci95': [0.8643042350907519, 0.9245852187028658], 'n': 500}, 'method': {'precision_ci95': [0.8159203980099502, 0.9406392694063926], 'recall_ci95': [0.545816733067729, 0.6851851851851852], 'n': 147}}`

## Expanded Proxy Alignment (Diagnostic)

- reducer_vs_enriched_truth_precision: `0.970016`
- reducer_vs_enriched_truth_recall: `0.855611`
- db_vs_enriched_truth_precision: `0.970016`
- db_vs_enriched_truth_recall: `0.855611`
- reducer_vs_enriched_truth_divergence_index: `0.166435`
- inclusion_policy: `{'base': 'contract_truth_edges + limitation_edges', 'scope_exclusions': ['standard_call', 'external'], 'limitation_focus': ['dynamic', 'in_repo_unresolved', 'relative_unresolved'], 'confidence_tiers': {'high': ['in_repo_unresolved'], 'low': ['dynamic', 'relative_unresolved']}, 'notes': 'Expanded truth is diagnostic-only and non-gating.'}`
- tier.high_conf: reducer_p/r=`0.970016`/`0.856836`, db_p/r=`0.970016`/`0.856836`, divergence=`0.165272`
- tier.full: reducer_p/r=`0.970016`/`0.855611`, db_p/r=`0.970016`/`0.855611`, divergence=`0.166435`
- tier_edge_counts: `{'high_conf_edges': 1397, 'full_edges': 1399}`
- scope_split_counts: `{'excluded_out_of_scope_edges': 4498, 'included_limitation_edges': 166, 'excluded_out_of_scope_by_reason': {'external': 4365, 'standard_call': 133}, 'included_limitation_by_reason': {'in_repo_unresolved': 163, 'dynamic': 3}}`
Reason-level expanded proxy recall:
- reason.dynamic: reducer_recall=`0.000000`, db_recall=`0.000000`, reducer_tp/fn=`0/2`
- reason.in_repo_unresolved: reducer_recall=`0.043478`, db_recall=`0.043478`, reducer_tp/fn=`3/66`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.9535080304311073, 0.981421647819063], 'recall_ci95': [0.8066770186335404, 0.8911651728553137], 'n': 500}}`

## Prompt Reliability (Heuristic Diagnostics)

- navigation_structural_reliability: `0.872549`
- reasoning_structural_reliability: `0.548604`
- coupling_stability_index: `0.967585`
- prompt_reliability_version: `v1`
- weights: `{'navigation': {'fp_weight': 1.0, 'fn_weight': 1.0}, 'reasoning': {'fp_weight': 1.0, 'fn_weight': 1.2}}`
- component_contributions: `{'navigation': {'tp': 89, 'fp': 12, 'fn': 1, 'penalty_fp': 12.0, 'penalty_fn': 1.0, 'denominator': 102.0}, 'reasoning': {'tp': 228, 'fp': 28, 'fn': 133, 'penalty_fp': 28.0, 'penalty_fn': 159.6, 'denominator': 415.6}}`
- enrichment_noise_ratio: `0.050751`

## Language Breakdown

- java: sampled_nodes=`205`, population_nodes=`7166`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`0.959212`/`0.921622`, expanded_p/r=`0.963432`/`0.870394`, contract_overreach=`0.040788`, projection_tp/fp/fn=`711/0/0`, contract_tp/fp/fn=`682/29/58`
- java:module: recall=`0.988095`, precision=`0.873684`, tp/fp/fn=`83/12/1`
- java:class: recall=`1.000000`, precision=`1.000000`, tp/fp/fn=`523/0/0`
- java:method: recall=`0.571429`, precision=`0.817204`, tp/fp/fn=`76/17/57`
- python: sampled_nodes=`266`, population_nodes=`1960`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`0.978723`/`0.869416`, expanded_p/r=`0.978723`/`0.834983`, contract_overreach=`0.021277`, projection_tp/fp/fn=`517/0/0`, contract_tp/fp/fn=`506/11/76`
- python:module: recall=`None`, precision=`None`, tp/fp/fn=`0/0/0`
- python:class: recall=`1.000000`, precision=`1.000000`, tp/fp/fn=`354/0/0`
- python:function: recall=`0.666667`, precision=`0.918919`, tp/fp/fn=`68/6/34`
- python:method: recall=`0.666667`, precision=`0.943820`, tp/fp/fn=`84/5/42`
- typescript: sampled_nodes=`29`, population_nodes=`29`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`1.000000`/`1.000000`, expanded_p/r=`1.000000`/`1.000000`, contract_overreach=`0.000000`, projection_tp/fp/fn=`6/0/0`, contract_tp/fp/fn=`6/0/0`
- typescript:module: recall=`1.000000`, precision=`1.000000`, tp/fp/fn=`6/0/0`
- typescript:function: recall=`None`, precision=`None`, tp/fp/fn=`0/0/0`

Expanded Proxy Alignment by language:kind
- java:module: strict_p/r=`0.873684`/`0.988095`, expanded_p/r=`0.873684`/`0.988095`
- java:class: strict_p/r=`1.000000`/`1.000000`, expanded_p/r=`1.000000`/`1.000000`
- java:method: strict_p/r=`0.817204`/`0.571429`, expanded_p/r=`0.849462`/`0.438889`
- python:module: strict_p/r=`None`/`None`, expanded_p/r=`None`/`None`
- python:class: strict_p/r=`1.000000`/`1.000000`, expanded_p/r=`1.000000`/`1.000000`
- python:function: strict_p/r=`0.918919`/`0.666667`, expanded_p/r=`0.918919`/`0.607143`
- python:method: strict_p/r=`0.943820`/`0.666667`, expanded_p/r=`0.943820`/`0.600000`
- typescript:module: strict_p/r=`1.000000`/`1.000000`, expanded_p/r=`1.000000`/`1.000000`
- typescript:function: strict_p/r=`None`/`None`, expanded_p/r=`None`/`None`

Strict vs Expanded delta by kind (top-5 worst recall delta)
- java:method: delta_recall=`0.132540`, delta_precision=`-0.032258`
- python:method: delta_recall=`0.066667`, delta_precision=`0.000000`
- python:function: delta_recall=`0.059524`, delta_precision=`0.000000`
- typescript:module: delta_recall=`0.000000`, delta_precision=`0.000000`
- python:class: delta_recall=`0.000000`, delta_precision=`0.000000`

## Call Resolution Diagnostics

- call_form.direct: tp=`1089`, fn=`85`, recall=`0.927598`
- call_form.member: tp=`108`, fn=`46`, recall=`0.701299`
- mismatch_attribution.core_missed_resolution: `0`
- mismatch_attribution.core_overresolution: `111`
- mismatch_attribution.normalization_contract_mismatch: `0`
- mismatch_attribution.independent_overprojection: `201`

## Out-of-Contract Distribution

- call: `166`

Breakdown by `edge_type::language::reason`:
- call::java::in_repo_unresolved: `140`
- call::python::dynamic: `3`
- call::python::in_repo_unresolved: `23`

Note: `enrichment_edges` includes only in-repo out-of-contract edges (unresolved, dynamic, standard-call filtered); external edges are excluded.

## Independent Parser Coverage & Totals

- coverage.java: files_parsed/files_total=`166/166` (1.000000)
- coverage.python: files_parsed/files_total=`115/115` (1.000000)
- coverage.typescript: files_parsed/files_total=`15/15` (1.000000)
- raw_call_edges: `28402`
- raw_import_edges: `5105`
- normalized_call_edges: `28402`
- normalized_import_edges: `5105`
- contract_truth_edges: `1328`
- enrichment_edges: `71`
- enriched_truth_edges: `1399`
- expanded_high_conf_edges: `1397`
- expanded_full_edges: `1399`
- excluded_out_of_scope_edges: `4498`
- included_limitation_edges: `166`

## Core Metrics

- static_contract_recall: `0.899096`
- static_overreach_rate: `0.032415`
- overreach_count: `40`
- reducer_edge_total: `1234`

## Action Priority Board

- [high] core_analysis::method_recall_gap evidence=`{'method_recall': 0.6177606177606177}`
- [medium] core_analysis::function_recall_gap evidence=`{'function_recall': 0.6666666666666666}`
- [medium] validation_workflow::strict_to_expanded_recall_drop evidence=`{'strict_recall': 0.8990963855421686, 'expanded_full_recall': 0.8556111508220158, 'delta': 0.043485234720152866}`
- [medium] core_analysis::reasoning_reliability_low evidence=`{'reasoning_structural_reliability': 0.548604427333975}`

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

