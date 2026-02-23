# SCIONA Reducer Validation Report

## Executive Summary

- repo=nest
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

- static_contract_precision: `0.937954`
- static_contract_recall: `0.941639`
- static_overreach_rate: `0.062046`
- static_divergence_index: `0.113576`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.9125560538116592, 0.9587053571428571], 'recall_ci95': [0.9255626081938835, 0.9585516912815627], 'n': 499}, 'method': {'precision_ci95': [0.4166666666666667, 0.6857142857142857], 'recall_ci95': [0.5067567567567568, 0.6854838709677419], 'n': 125}}`

## Expanded Proxy Alignment (Diagnostic)

- reducer_vs_enriched_truth_precision: `0.939072`
- reducer_vs_enriched_truth_recall: `0.887012`
- db_vs_enriched_truth_precision: `0.939072`
- db_vs_enriched_truth_recall: `0.887012`
- reducer_vs_enriched_truth_divergence_index: `0.161258`
- inclusion_policy: `{'base': 'contract_truth_edges + limitation_edges', 'scope_exclusions': ['standard_call', 'external'], 'limitation_focus': ['dynamic', 'in_repo_unresolved', 'relative_unresolved'], 'confidence_tiers': {'high': ['in_repo_unresolved'], 'low': ['dynamic', 'relative_unresolved']}, 'notes': 'Expanded truth is diagnostic-only and non-gating.'}`
- tier.high_conf: reducer_p/r=`0.939072`/`0.899839`, db_p/r=`0.939072`/`0.899839`, divergence=`0.149798`
- tier.full: reducer_p/r=`0.939072`/`0.887012`, db_p/r=`0.939072`/`0.887012`, divergence=`0.161258`
- tier_edge_counts: `{'high_conf_edges': 1867, 'full_edges': 1894}`
- scope_split_counts: `{'excluded_out_of_scope_edges': 781, 'included_limitation_edges': 134, 'excluded_out_of_scope_by_reason': {'external': 707, 'standard_call': 74}, 'included_limitation_by_reason': {'in_repo_unresolved': 102, 'dynamic': 32}}`
Reason-level expanded proxy recall:
- reason.dynamic: reducer_recall=`0.000000`, db_recall=`0.000000`, reducer_tp/fn=`0/27`
- reason.in_repo_unresolved: reducer_recall=`0.023529`, db_recall=`0.023529`, reducer_tp/fn=`2/83`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.9140625, 0.9579632918886916], 'recall_ci95': [0.8581453634085213, 0.9100397614314115], 'n': 499}}`

## Prompt Reliability (Heuristic Diagnostics)

- navigation_structural_reliability: `0.998162`
- reasoning_structural_reliability: `0.495803`
- coupling_stability_index: `0.937954`
- prompt_reliability_version: `v1`
- weights: `{'navigation': {'fp_weight': 1.0, 'fn_weight': 1.0}, 'reasoning': {'fp_weight': 1.0, 'fn_weight': 1.2}}`
- component_contributions: `{'navigation': {'tp': 543, 'fp': 1, 'fn': 0, 'penalty_fp': 1.0, 'penalty_fn': 0.0, 'denominator': 544.0}, 'reasoning': {'tp': 189, 'fp': 71, 'fn': 101, 'penalty_fp': 71.0, 'penalty_fn': 121.19999999999999, 'denominator': 381.2}}`
- enrichment_noise_ratio: `0.059134`

## Language Breakdown

- typescript: sampled_nodes=`500`, population_nodes=`6033`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`0.937954`/`0.941639`, expanded_p/r=`0.939072`/`0.887012`, contract_overreach=`0.062046`, projection_tp/fp/fn=`1791/0/0`, contract_tp/fp/fn=`1678/111/104`
- typescript:module: recall=`1.000000`, precision=`0.998162`, tp/fp/fn=`543/1/0`
- typescript:class: recall=`0.996839`, precision=`0.960406`, tp/fp/fn=`946/39/3`
- typescript:function: recall=`0.687500`, precision=`0.924370`, tp/fp/fn=`110/9/50`
- typescript:method: recall=`0.607692`, precision=`0.560284`, tp/fp/fn=`79/62/51`

Expanded Proxy Alignment by language:kind
- typescript:module: strict_p/r=`0.998162`/`1.000000`, expanded_p/r=`0.998162`/`1.000000`
- typescript:class: strict_p/r=`0.960406`/`0.996839`, expanded_p/r=`0.960406`/`0.996839`
- typescript:function: strict_p/r=`0.924370`/`0.687500`, expanded_p/r=`0.924370`/`0.440000`
- typescript:method: strict_p/r=`0.560284`/`0.607692`, expanded_p/r=`0.574468`/`0.532895`

Strict vs Expanded delta by kind (top-5 worst recall delta)
- typescript:function: delta_recall=`0.247500`, delta_precision=`0.000000`
- typescript:method: delta_recall=`0.074798`, delta_precision=`-0.014184`
- typescript:module: delta_recall=`0.000000`, delta_precision=`0.000000`
- typescript:class: delta_recall=`0.000000`, delta_precision=`0.000000`

## Call Resolution Diagnostics

- call_form.direct: tp=`1600`, fn=`50`, recall=`0.969697`
- call_form.member: tp=`79`, fn=`53`, recall=`0.598485`
- mismatch_attribution.core_missed_resolution: `0`
- mismatch_attribution.core_overresolution: `645`
- mismatch_attribution.normalization_contract_mismatch: `0`
- mismatch_attribution.independent_overprojection: `635`

## Out-of-Contract Distribution

- call: `134`

Breakdown by `edge_type::language::reason`:
- call::typescript::dynamic: `32`
- call::typescript::in_repo_unresolved: `102`

Note: `enrichment_edges` includes only in-repo out-of-contract edges (unresolved, dynamic, standard-call filtered); external edges are excluded.

## Independent Parser Coverage & Totals

- coverage.typescript: files_parsed/files_total=`338/338` (1.000000)
- raw_call_edges: `16619`
- raw_import_edges: `1905`
- normalized_call_edges: `16619`
- normalized_import_edges: `1905`
- contract_truth_edges: `1782`
- enrichment_edges: `112`
- enriched_truth_edges: `1894`
- expanded_high_conf_edges: `1867`
- expanded_full_edges: `1894`
- excluded_out_of_scope_edges: `781`
- included_limitation_edges: `134`

## Core Metrics

- static_contract_recall: `0.941639`
- static_overreach_rate: `0.062046`
- overreach_count: `111`
- reducer_edge_total: `1791`

## Action Priority Board

- [high] core_analysis::method_recall_gap evidence=`{'method_recall': 0.6076923076923076}`
- [high] core_analysis::method_precision_gap evidence=`{'method_precision': 0.5602836879432624}`
- [high] core_analysis::strict_overreach_elevated evidence=`{'strict_overreach_rate': 0.06204583566238122}`
- [medium] core_analysis::function_recall_gap evidence=`{'function_recall': 0.6875}`
- [medium] validation_workflow::strict_to_expanded_recall_drop evidence=`{'strict_recall': 0.941638608305275, 'expanded_full_recall': 0.8870116156282999, 'delta': 0.05462699267697513}`
- [medium] core_analysis::reasoning_reliability_low evidence=`{'reasoning_structural_reliability': 0.49580272822665267}`

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

