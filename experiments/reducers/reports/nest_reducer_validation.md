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

- static_contract_precision: `0.961032`
- static_contract_recall: `0.935826`
- static_overreach_rate: `0.038968`
- static_divergence_index: `0.098387`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.9387521465369204, 0.9777536625067824], 'recall_ci95': [0.9165207238762405, 0.9505110274341043], 'n': 499}, 'method': {'precision_ci95': [0.9285714285714286, 0.9878048780487805], 'recall_ci95': [0.6232558139534884, 0.7380952380952381], 'n': 125}}`

## Expanded Proxy Alignment (Diagnostic)

- reducer_vs_enriched_truth_precision: `0.962751`
- reducer_vs_enriched_truth_recall: `0.870016`
- db_vs_enriched_truth_precision: `0.962751`
- db_vs_enriched_truth_recall: `0.870016`
- reducer_vs_enriched_truth_divergence_index: `0.158317`
- inclusion_policy: `{'base': 'contract_truth_edges + limitation_edges', 'scope_exclusions': ['standard_call', 'external'], 'limitation_focus': ['dynamic', 'in_repo_unresolved', 'relative_unresolved'], 'confidence_tiers': {'high': ['in_repo_unresolved'], 'low': ['dynamic', 'relative_unresolved']}, 'notes': 'Expanded truth is diagnostic-only and non-gating.'}`
- tier.high_conf: reducer_p/r=`0.962751`/`0.883745`, db_p/r=`0.962751`/`0.883745`, divergence=`0.145473`
- tier.full: reducer_p/r=`0.962751`/`0.870016`, db_p/r=`0.962751`/`0.870016`, divergence=`0.158317`
- tier_edge_counts: `{'high_conf_edges': 1901, 'full_edges': 1931}`
- scope_split_counts: `{'excluded_out_of_scope_edges': 841, 'included_limitation_edges': 163, 'excluded_out_of_scope_by_reason': {'external': 771, 'standard_call': 70}, 'included_limitation_by_reason': {'dynamic': 33, 'in_repo_unresolved': 130}}`
Reason-level expanded proxy recall:
- reason.dynamic: reducer_recall=`0.000000`, db_recall=`0.000000`, reducer_tp/fn=`0/30`
- reason.in_repo_unresolved: reducer_recall=`0.027523`, db_recall=`0.027523`, reducer_tp/fn=`3/106`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.9403234802007808, 0.9801790281329923], 'recall_ci95': [0.8424769147202608, 0.895397489539749], 'n': 499}}`

## Prompt Reliability (Heuristic Diagnostics)

- navigation_structural_reliability: `0.997992`
- reasoning_structural_reliability: `0.602527`
- coupling_stability_index: `0.961032`
- prompt_reliability_version: `v1`
- weights: `{'navigation': {'fp_weight': 1.0, 'fn_weight': 1.0}, 'reasoning': {'fp_weight': 1.0, 'fn_weight': 1.2}}`
- component_contributions: `{'navigation': {'tp': 497, 'fp': 1, 'fn': 0, 'penalty_fp': 1.0, 'penalty_fn': 0.0, 'denominator': 498.0}, 'reasoning': {'tp': 248, 'fp': 28, 'fn': 113, 'penalty_fp': 28.0, 'penalty_fn': 135.6, 'denominator': 411.6}}`
- enrichment_noise_ratio: `0.071983`

## Language Breakdown

- typescript: sampled_nodes=`500`, population_nodes=`6033`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`0.961032`/`0.935826`, expanded_p/r=`0.962751`/`0.870016`, contract_overreach=`0.038968`, projection_tp/fp/fn=`1747/0/0`, contract_tp/fp/fn=`1677/68/115`
- typescript:module: recall=`1.000000`, precision=`0.997992`, tp/fp/fn=`497/1/0`
- typescript:class: recall=`0.997859`, precision=`0.959835`, tp/fp/fn=`932/39/2`
- typescript:function: recall=`0.690647`, precision=`0.813559`, tp/fp/fn=`96/22/43`
- typescript:method: recall=`0.684685`, precision=`0.962025`, tp/fp/fn=`152/6/70`

Expanded Proxy Alignment by language:kind
- typescript:module: strict_p/r=`0.997992`/`1.000000`, expanded_p/r=`0.997992`/`1.000000`
- typescript:class: strict_p/r=`0.959835`/`0.997859`, expanded_p/r=`0.959835`/`0.997859`
- typescript:function: strict_p/r=`0.813559`/`0.690647`, expanded_p/r=`0.813559`/`0.415584`
- typescript:method: strict_p/r=`0.962025`/`0.684685`, expanded_p/r=`0.981013`/`0.576208`

Strict vs Expanded delta by kind (top-5 worst recall delta)
- typescript:function: delta_recall=`0.275063`, delta_precision=`0.000000`
- typescript:method: delta_recall=`0.108477`, delta_precision=`-0.018987`
- typescript:module: delta_recall=`0.000000`, delta_precision=`0.000000`
- typescript:class: delta_recall=`0.000000`, delta_precision=`0.000000`

## Call Resolution Diagnostics

- call_form.direct: tp=`1532`, fn=`44`, recall=`0.972081`
- call_form.member: tp=`145`, fn=`71`, recall=`0.671296`
- mismatch_attribution.core_missed_resolution: `0`
- mismatch_attribution.core_overresolution: `73`
- mismatch_attribution.normalization_contract_mismatch: `0`
- mismatch_attribution.independent_overprojection: `117`
- resolution.accepted_by_provenance: `{'exact_qname': 275, 'import_narrowed': 1}`
- resolution.dropped_by_reason: `{'unique_without_provenance': 3, 'no_candidates': 12, 'ambiguous_no_in_scope_candidate': 3}`
- resolution.candidate_count_histogram: `{'1': 278, '0': 12, '10': 1, '13': 1, '2': 1, '12': 1}`
- resolution.record_drops: `{'no_resolved_callees': 3}`
- resolution.typescript:function: accepted=`{'exact_qname': 118}`, dropped=`{}`
- resolution.typescript:method: accepted=`{'exact_qname': 157, 'import_narrowed': 1}`, dropped=`{'unique_without_provenance': 3, 'no_candidates': 12, 'ambiguous_no_in_scope_candidate': 3}`

## Class Mapping Reliability

- class_rows_parse_ok_with_methods: `92`
- class_rows_unreliable_mapping: `0`
- class_rows_scored: `92`
- unreliable_mapping_rate: `0.000000`

## Out-of-Contract Distribution

- call: `163`

Breakdown by `edge_type::language::reason`:
- call::typescript::dynamic: `33`
- call::typescript::in_repo_unresolved: `130`

Note: `enrichment_edges` includes only in-repo out-of-contract edges (unresolved, dynamic, standard-call filtered); external edges are excluded.

## Independent Parser Coverage & Totals

- coverage.typescript: files_parsed/files_total=`344/344` (1.000000)
- raw_call_edges: `16260`
- raw_import_edges: `1920`
- normalized_call_edges: `16260`
- normalized_import_edges: `1920`
- contract_truth_edges: `1792`
- enrichment_edges: `139`
- enriched_truth_edges: `1931`
- expanded_high_conf_edges: `1901`
- expanded_full_edges: `1931`
- excluded_out_of_scope_edges: `841`
- included_limitation_edges: `163`

## Core Metrics

- static_contract_recall: `0.935826`
- static_overreach_rate: `0.038968`
- overreach_count: `68`
- reducer_edge_total: `1747`

## Action Priority Board

- [high] core_analysis::method_recall_gap evidence=`{'method_recall': 0.6846846846846847}`
- [medium] core_analysis::function_recall_gap evidence=`{'function_recall': 0.6906474820143885}`
- [medium] validation_workflow::strict_to_expanded_recall_drop evidence=`{'strict_recall': 0.9358258928571429, 'expanded_full_recall': 0.8700155359917141, 'delta': 0.0658103568654288}`
- [medium] core_analysis::reasoning_reliability_low evidence=`{'reasoning_structural_reliability': 0.6025267249757046}`

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

