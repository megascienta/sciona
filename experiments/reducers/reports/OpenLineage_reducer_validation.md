# SCIONA Reducer Validation Report

## Executive Summary

- repo=OpenLineage
- sampled_nodes=1500
- invariants_passed=True

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

- static_contract_precision: `0.911565`
- static_contract_recall: `0.971321`
- static_overreach_rate: `0.088435`
- static_divergence_index: `0.112327`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.8947844437744951, 0.9253602305475505], 'recall_ci95': [0.9637854458489922, 0.9771997430956969], 'n': 1500}, 'method': {'precision_ci95': [0.7037533512064343, 0.7962962962962963], 'recall_ci95': [0.8842443729903537, 0.9325259515570934], 'n': 457}}`

## Expanded Truth Alignment (Diagnostic)

- reducer_vs_enriched_truth_precision: `0.914522`
- reducer_vs_enriched_truth_recall: `0.856035`
- db_vs_enriched_truth_precision: `0.914522`
- db_vs_enriched_truth_recall: `0.856035`
- reducer_vs_enriched_truth_divergence_index: `0.207383`
- inclusion_policy: `{'base': 'contract_truth_edges + limitation_edges', 'scope_exclusions': ['standard_call', 'external'], 'limitation_focus': ['dynamic', 'in_repo_unresolved', 'relative_unresolved'], 'confidence_tiers': {'high': ['in_repo_unresolved'], 'low': ['dynamic', 'relative_unresolved']}, 'notes': 'Expanded truth is diagnostic-only and non-gating.'}`
- tier.high_conf: reducer_p/r=`0.914522`/`0.856747`, db_p/r=`0.914522`/`0.856747`, divergence=`0.206773`
- tier.full: reducer_p/r=`0.914522`/`0.856035`, db_p/r=`0.914522`/`0.856035`, divergence=`0.207383`
- tier_edge_counts: `{'high_conf_edges': 3609, 'full_edges': 3612}`
- scope_split_counts: `{'excluded_out_of_scope_edges': 10903, 'included_limitation_edges': 636, 'excluded_out_of_scope_by_reason': {'external': 10575, 'standard_call': 328}, 'included_limitation_by_reason': {'in_repo_unresolved': 633, 'dynamic': 3}}`
Reason-level expanded recall:
- reason.dynamic: reducer_recall=`0.000000`, db_recall=`0.000000`, reducer_tp/fn=`0/3`
- reason.in_repo_unresolved: reducer_recall=`0.022936`, db_recall=`0.022936`, reducer_tp/fn=`10/426`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.8987937628714328, 0.9286346210557358], 'recall_ci95': [0.8356860530773574, 0.8746231155778894], 'n': 1500}}`

## Prompt Reliability (Heuristic Diagnostics)

- navigation_structural_reliability: `0.854077`
- reasoning_structural_reliability: `0.668677`
- coupling_stability_index: `0.911565`
- prompt_reliability_version: `v1`
- weights: `{'navigation': {'fp_weight': 1.0, 'fn_weight': 1.0}, 'reasoning': {'fp_weight': 1.0, 'fn_weight': 1.2}}`
- component_contributions: `{'navigation': {'tp': 199, 'fp': 31, 'fn': 3, 'penalty_fp': 31.0, 'penalty_fn': 3.0, 'denominator': 233.0}, 'reasoning': {'tp': 754, 'fp': 268, 'fn': 88, 'penalty_fp': 268.0, 'penalty_fn': 105.6, 'denominator': 1127.6}}`
- enrichment_noise_ratio: `0.121539`

## Language Breakdown

- java: sampled_nodes=`633`, population_nodes=`7166`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`0.918568`/`0.982297`, expanded_p/r=`0.923043`/`0.876381`, contract_overreach=`0.081432`, projection_tp/fp/fn=`2235/0/0`, contract_tp/fp/fn=`2053/182/37`
- java:module: recall=`0.984694`, precision=`0.861607`, tp/fp/fn=`193/31/3`
- java:class: recall=`1.000000`, precision=`1.000000`, tp/fp/fn=`1595/0/0`
- java:method: recall=`0.886288`, precision=`0.637019`, tp/fp/fn=`265/151/34`
- python: sampled_nodes=`838`, population_nodes=`1960`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`0.898067`/`0.949814`, expanded_p/r=`0.898067`/`0.818255`, contract_overreach=`0.101933`, projection_tp/fp/fn=`1138/0/0`, contract_tp/fp/fn=`1022/116/54`
- python:module: recall=`None`, precision=`None`, tp/fp/fn=`0/0/0`
- python:class: recall=`1.000000`, precision=`1.000000`, tp/fp/fn=`534/0/0`
- python:function: recall=`0.857143`, precision=`0.709677`, tp/fp/fn=`198/81/33`
- python:method: recall=`0.932476`, precision=`0.892308`, tp/fp/fn=`290/35/21`
- typescript: sampled_nodes=`29`, population_nodes=`29`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`0.875000`/`1.000000`, expanded_p/r=`0.875000`/`0.777778`, contract_overreach=`0.125000`, projection_tp/fp/fn=`8/0/0`, contract_tp/fp/fn=`7/1/0`
- typescript:module: recall=`1.000000`, precision=`1.000000`, tp/fp/fn=`6/0/0`
- typescript:function: recall=`1.000000`, precision=`0.500000`, tp/fp/fn=`1/1/0`

Expanded Alignment by language:kind
- java:module: strict_p/r=`0.861607`/`0.984694`, expanded_p/r=`0.861607`/`0.984694`
- java:class: strict_p/r=`1.000000`/`1.000000`, expanded_p/r=`1.000000`/`1.000000`
- java:method: strict_p/r=`0.637019`/`0.886288`, expanded_p/r=`0.661058`/`0.488455`
- python:module: strict_p/r=`None`/`None`, expanded_p/r=`None`/`None`
- python:class: strict_p/r=`1.000000`/`1.000000`, expanded_p/r=`1.000000`/`1.000000`
- python:function: strict_p/r=`0.709677`/`0.857143`, expanded_p/r=`0.709677`/`0.640777`
- python:method: strict_p/r=`0.892308`/`0.932476`, expanded_p/r=`0.892308`/`0.714286`
- typescript:module: strict_p/r=`1.000000`/`1.000000`, expanded_p/r=`1.000000`/`1.000000`
- typescript:function: strict_p/r=`0.500000`/`1.000000`, expanded_p/r=`0.500000`/`0.333333`

Strict vs Expanded delta by kind (top-5 worst recall delta)
- typescript:function: delta_recall=`0.666667`, delta_precision=`0.000000`
- java:method: delta_recall=`0.397833`, delta_precision=`-0.024038`
- python:method: delta_recall=`0.218190`, delta_precision=`0.000000`
- python:function: delta_recall=`0.216366`, delta_precision=`0.000000`
- typescript:module: delta_recall=`0.000000`, delta_precision=`0.000000`

## Call Resolution Diagnostics

- call_form.direct: tp=`2857`, fn=`39`, recall=`0.986533`
- call_form.member: tp=`226`, fn=`51`, recall=`0.815884`
- mismatch_attribution.core_missed_resolution: `0`
- mismatch_attribution.core_overresolution: `750`
- mismatch_attribution.normalization_contract_mismatch: `0`
- mismatch_attribution.independent_overprojection: `530`

## Out-of-Contract Distribution

- call: `636`

Breakdown by `edge_type::language::reason`:
- call::java::dynamic: `3`
- call::java::in_repo_unresolved: `410`
- call::python::in_repo_unresolved: `221`
- call::typescript::in_repo_unresolved: `2`

Note: `enrichment_edges` includes only in-repo out-of-contract edges (unresolved, dynamic, standard-call filtered); external edges are excluded.

## Independent Parser Coverage & Totals

- coverage.java: files_parsed/files_total=`400/400` (1.000000)
- coverage.python: files_parsed/files_total=`196/196` (1.000000)
- coverage.typescript: files_parsed/files_total=`15/15` (1.000000)
- raw_call_edges: `46276`
- raw_import_edges: `9064`
- normalized_call_edges: `46276`
- normalized_import_edges: `9064`
- contract_truth_edges: `3173`
- enrichment_edges: `439`
- enriched_truth_edges: `3612`
- expanded_high_conf_edges: `3609`
- expanded_full_edges: `3612`
- excluded_out_of_scope_edges: `10903`
- included_limitation_edges: `636`

## Core Metrics

- static_contract_recall: `0.971321`
- static_overreach_rate: `0.088435`
- overreach_count: `299`
- reducer_edge_total: `3381`

## Action Priority Board

- [high] core_analysis::method_precision_gap evidence=`{'method_precision': 0.7489878542510121}`
- [high] core_analysis::strict_overreach_elevated evidence=`{'strict_overreach_rate': 0.08843537414965986}`
- [medium] core_analysis::function_recall_gap evidence=`{'function_recall': 0.8577586206896551}`
- [medium] validation_workflow::strict_to_expanded_recall_drop evidence=`{'strict_recall': 0.9713205168610148, 'expanded_full_recall': 0.8560354374307863, 'delta': 0.11528507943022859}`
- [medium] core_analysis::reasoning_reliability_low evidence=`{'reasoning_structural_reliability': 0.6686768357573608}`

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

