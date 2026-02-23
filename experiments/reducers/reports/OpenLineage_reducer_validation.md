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

- static_contract_precision: `0.979646`
- static_contract_recall: `0.884185`
- static_overreach_rate: `0.020354`
- static_divergence_index: `0.131765`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.9666666666666667, 0.988929889298893], 'recall_ci95': [0.8513957307060755, 0.9117451891174518], 'n': 500}, 'method': {'precision_ci95': [0.8786127167630058, 0.9846938775510204], 'recall_ci95': [0.5084745762711864, 0.6738351254480287], 'n': 144}}`

## Expanded Proxy Alignment (Diagnostic)

- reducer_vs_enriched_truth_precision: `0.979646`
- reducer_vs_enriched_truth_recall: `0.830458`
- db_vs_enriched_truth_precision: `0.979646`
- db_vs_enriched_truth_recall: `0.830458`
- reducer_vs_enriched_truth_divergence_index: `0.183628`
- inclusion_policy: `{'base': 'contract_truth_edges + limitation_edges', 'scope_exclusions': ['standard_call', 'external'], 'limitation_focus': ['dynamic', 'in_repo_unresolved', 'relative_unresolved'], 'confidence_tiers': {'high': ['in_repo_unresolved'], 'low': ['dynamic', 'relative_unresolved']}, 'notes': 'Expanded truth is diagnostic-only and non-gating.'}`
- tier.high_conf: reducer_p/r=`0.979646`/`0.831081`, db_p/r=`0.979646`/`0.831081`, divergence=`0.183026`
- tier.full: reducer_p/r=`0.979646`/`0.830458`, db_p/r=`0.979646`/`0.830458`, divergence=`0.183628`
- tier_edge_counts: `{'high_conf_edges': 1332, 'full_edges': 1333}`
- scope_split_counts: `{'excluded_out_of_scope_edges': 4205, 'included_limitation_edges': 165, 'excluded_out_of_scope_by_reason': {'external': 4048, 'standard_call': 157}, 'included_limitation_by_reason': {'in_repo_unresolved': 162, 'dynamic': 3}}`
Reason-level expanded proxy recall:
- reason.dynamic: reducer_recall=`0.000000`, db_recall=`0.000000`, reducer_tp/fn=`0/1`
- reason.in_repo_unresolved: reducer_recall=`0.000000`, db_recall=`0.000000`, reducer_tp/fn=`0/80`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.9677137870855148, 0.9891304347826086], 'recall_ci95': [0.7862016679302501, 0.8708430007733952], 'n': 500}}`

## Prompt Reliability (Heuristic Diagnostics)

- navigation_structural_reliability: `0.808824`
- reasoning_structural_reliability: `0.533266`
- coupling_stability_index: `0.979646`
- prompt_reliability_version: `v1`
- weights: `{'navigation': {'fp_weight': 1.0, 'fn_weight': 1.0}, 'reasoning': {'fp_weight': 1.0, 'fn_weight': 1.2}}`
- component_contributions: `{'navigation': {'tp': 55, 'fp': 12, 'fn': 1, 'penalty_fp': 12.0, 'penalty_fn': 1.0, 'denominator': 68.0}, 'reasoning': {'tp': 210, 'fp': 11, 'fn': 144, 'penalty_fp': 11.0, 'penalty_fn': 172.79999999999998, 'denominator': 393.79999999999995}}`
- enrichment_noise_ratio: `0.060765`

## Language Breakdown

- java: sampled_nodes=`204`, population_nodes=`7166`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`0.974318`/`0.912782`, expanded_p/r=`0.974318`/`0.841886`, contract_overreach=`0.025682`, projection_tp/fp/fn=`623/0/0`, contract_tp/fp/fn=`607/16/58`
- java:module: recall=`0.980000`, precision=`0.803279`, tp/fp/fn=`49/12/1`
- java:class: recall=`1.000000`, precision=`1.000000`, tp/fp/fn=`491/0/0`
- java:method: recall=`0.540323`, precision=`0.943662`, tp/fp/fn=`67/4/57`
- python: sampled_nodes=`267`, population_nodes=`1960`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`0.986028`/`0.853195`, expanded_p/r=`0.986028`/`0.819237`, contract_overreach=`0.013972`, projection_tp/fp/fn=`501/0/0`, contract_tp/fp/fn=`494/7/85`
- python:module: recall=`None`, precision=`None`, tp/fp/fn=`0/0/0`
- python:class: recall=`1.000000`, precision=`1.000000`, tp/fp/fn=`351/0/0`
- python:function: recall=`0.586957`, precision=`0.981818`, tp/fp/fn=`54/1/38`
- python:method: recall=`0.654412`, precision=`0.936842`, tp/fp/fn=`89/6/47`
- typescript: sampled_nodes=`29`, population_nodes=`29`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`1.000000`/`0.750000`, expanded_p/r=`1.000000`/`0.666667`, contract_overreach=`0.000000`, projection_tp/fp/fn=`6/0/0`, contract_tp/fp/fn=`6/0/2`
- typescript:module: recall=`1.000000`, precision=`1.000000`, tp/fp/fn=`6/0/0`
- typescript:function: recall=`0.000000`, precision=`None`, tp/fp/fn=`0/0/2`

Expanded Proxy Alignment by language:kind
- java:module: strict_p/r=`0.803279`/`0.980000`, expanded_p/r=`0.803279`/`0.980000`
- java:class: strict_p/r=`1.000000`/`1.000000`, expanded_p/r=`1.000000`/`1.000000`
- java:method: strict_p/r=`0.943662`/`0.540323`, expanded_p/r=`0.943662`/`0.372222`
- python:module: strict_p/r=`None`/`None`, expanded_p/r=`None`/`None`
- python:class: strict_p/r=`1.000000`/`1.000000`, expanded_p/r=`1.000000`/`1.000000`
- python:function: strict_p/r=`0.981818`/`0.586957`, expanded_p/r=`0.981818`/`0.524272`
- python:method: strict_p/r=`0.936842`/`0.654412`, expanded_p/r=`0.936842`/`0.597315`
- typescript:module: strict_p/r=`1.000000`/`1.000000`, expanded_p/r=`1.000000`/`1.000000`
- typescript:function: strict_p/r=`None`/`0.000000`, expanded_p/r=`None`/`0.000000`

Strict vs Expanded delta by kind (top-5 worst recall delta)
- java:method: delta_recall=`0.168100`, delta_precision=`0.000000`
- python:function: delta_recall=`0.062685`, delta_precision=`0.000000`
- python:method: delta_recall=`0.057096`, delta_precision=`0.000000`
- typescript:module: delta_recall=`0.000000`, delta_precision=`0.000000`
- typescript:function: delta_recall=`0.000000`, delta_precision=`None`

## Call Resolution Diagnostics

- call_form.direct: tp=`1007`, fn=`93`, recall=`0.915455`
- call_form.member: tp=`101`, fn=`51`, recall=`0.664474`
- mismatch_attribution.core_missed_resolution: `0`
- mismatch_attribution.core_overresolution: `89`
- mismatch_attribution.normalization_contract_mismatch: `0`
- mismatch_attribution.independent_overprojection: `208`
- resolution.accepted_by_provenance: `{'exact_qname': 210, 'import_narrowed': 15, 'module_scoped': 1}`
- resolution.dropped_by_reason: `{'no_candidates': 170, 'unique_without_provenance': 42, 'ambiguous_no_in_scope_candidate': 51, 'ambiguous_multiple_in_scope_candidates': 5}`
- resolution.candidate_count_histogram: `{'1': 253, '0': 170, '2': 13, '3': 14, '35': 2, '4': 9, '54': 4, '6': 2, '7': 2, '9': 1, '40': 1, '36': 5, '119': 2, '8': 4, '41': 1, '125': 2, '12': 3, '18': 1, '27': 3, '23': 1, '11': 1}`
- resolution.record_drops: `{'no_resolved_callees': 14, 'duplicate_caller_record': 5}`
- resolution.java:method: accepted=`{'exact_qname': 60, 'import_narrowed': 15, 'module_scoped': 1}`, dropped=`{'no_candidates': 170, 'unique_without_provenance': 42, 'ambiguous_no_in_scope_candidate': 51, 'ambiguous_multiple_in_scope_candidates': 5}`
- resolution.python:function: accepted=`{'exact_qname': 55}`, dropped=`{}`
- resolution.python:method: accepted=`{'exact_qname': 95}`, dropped=`{}`

## Class Mapping Reliability

- class_rows_parse_ok_with_methods: `121`
- class_rows_unreliable_mapping: `0`
- class_rows_scored: `121`
- unreliable_mapping_rate: `0.000000`

## Out-of-Contract Distribution

- call: `165`

Breakdown by `edge_type::language::reason`:
- call::java::dynamic: `3`
- call::java::in_repo_unresolved: `137`
- call::python::in_repo_unresolved: `24`
- call::typescript::in_repo_unresolved: `1`

Note: `enrichment_edges` includes only in-repo out-of-contract edges (unresolved, dynamic, standard-call filtered); external edges are excluded.

## Independent Parser Coverage & Totals

- coverage.java: files_parsed/files_total=`172/172` (1.000000)
- coverage.python: files_parsed/files_total=`135/135` (1.000000)
- coverage.typescript: files_parsed/files_total=`15/15` (1.000000)
- raw_call_edges: `27224`
- raw_import_edges: `4992`
- normalized_call_edges: `27224`
- normalized_import_edges: `4992`
- contract_truth_edges: `1252`
- enrichment_edges: `81`
- enriched_truth_edges: `1333`
- expanded_high_conf_edges: `1332`
- expanded_full_edges: `1333`
- excluded_out_of_scope_edges: `4205`
- included_limitation_edges: `165`

## Core Metrics

- static_contract_recall: `0.884185`
- static_overreach_rate: `0.020354`
- overreach_count: `23`
- reducer_edge_total: `1130`

## Action Priority Board

- [high] core_analysis::method_recall_gap evidence=`{'method_recall': 0.6}`
- [medium] core_analysis::function_recall_gap evidence=`{'function_recall': 0.574468085106383}`
- [medium] validation_workflow::strict_to_expanded_recall_drop evidence=`{'strict_recall': 0.884185303514377, 'expanded_full_recall': 0.8304576144036009, 'delta': 0.05372768911077608}`
- [medium] core_analysis::reasoning_reliability_low evidence=`{'reasoning_structural_reliability': 0.5332656170644998}`

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

