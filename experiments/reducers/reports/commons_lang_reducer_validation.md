# SCIONA Reducer Validation Report

## Executive Summary

- repo=commons_lang
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
- gate_member_call_recall_min: `None`
- gate_equal_contract_metrics_when_exact: `True`

## Internal Integrity (Hard Gates)

- valid: `True`
- static_projection_precision: `1.000000`
- static_projection_recall: `1.000000`
- parser_stability_score: `1.000000`

## Strict Contract Alignment (Gating)

- static_contract_precision: `0.972917`
- static_contract_recall: `0.998077`
- static_overreach_rate: `0.027083`
- static_divergence_index: `0.028904`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.961671546446633, 0.979491133384734], 'recall_ci95': [0.9968203497615262, 0.9992574257425743], 'n': 499}, 'method': {'precision_ci95': [0.2076923076923077, 0.3893129770992366], 'recall_ci95': [0.8611111111111112, 1.0], 'n': 167}}`

## Enrichment Alignment (Non-Gating Diagnostics)

- reducer_vs_enriched_truth_precision: `0.973542`
- reducer_vs_enriched_truth_recall: `0.973339`
- db_vs_enriched_truth_precision: `0.973542`
- db_vs_enriched_truth_recall: `0.973339`
- reducer_vs_enriched_truth_divergence_index: `0.051745`
- inclusion_policy: `{'base': 'contract_truth_edges + limitation_edges', 'scope_exclusions': ['standard_call', 'external'], 'limitation_focus': ['dynamic', 'in_repo_unresolved', 'relative_unresolved'], 'confidence_tiers': {'high': ['in_repo_unresolved'], 'low': ['dynamic', 'relative_unresolved']}, 'notes': 'Expanded truth is diagnostic-only and non-gating.'}`
- tier.high_conf: reducer_p/r=`0.973542`/`0.973339`, db_p/r=`0.973542`/`0.973339`, divergence=`0.051745`
- tier.full: reducer_p/r=`0.973542`/`0.973339`, db_p/r=`0.973542`/`0.973339`, divergence=`0.051745`
- tier_edge_counts: `{'high_conf_edges': 4801, 'full_edges': 4801}`
- scope_split_counts: `{'excluded_out_of_scope_edges': 3257, 'included_limitation_edges': 1936, 'excluded_out_of_scope_by_reason': {'external': 3234, 'standard_call': 23}, 'included_limitation_by_reason': {'in_repo_unresolved': 1936}}`
Reason-level expanded proxy recall:
- reason.in_repo_unresolved: reducer_recall=`0.024590`, db_recall=`0.024590`, reducer_tp/fn=`3/119`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.9636406286652592, 0.9805550645218314], 'recall_ci95': [0.9614778103176391, 0.9823572208075664], 'n': 499}}`

## Enrichment Reliability (Heuristic)

- navigation_structural_reliability: `0.831818`
- reasoning_structural_reliability: `0.287611`
- coupling_stability_index: `0.972917`
- prompt_reliability_version: `v1`
- weights: `{'navigation': {'fp_weight': 1.0, 'fn_weight': 1.0}, 'reasoning': {'fp_weight': 1.0, 'fn_weight': 1.2}}`
- component_contributions: `{'navigation': {'tp': 183, 'fp': 37, 'fn': 0, 'penalty_fp': 37.0, 'penalty_fn': 0.0, 'denominator': 220.0}, 'reasoning': {'tp': 39, 'fp': 93, 'fn': 3, 'penalty_fp': 93.0, 'penalty_fn': 3.5999999999999996, 'denominator': 135.6}}`
- enrichment_noise_ratio: `0.025411`

## Language Breakdown

- java: sampled_nodes=`500`, population_nodes=`9883`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`0.972917`/`0.998077`, expanded_p/r=`0.973542`/`0.973339`, contract_overreach=`0.027083`, projection_tp/fp/fn=`4802/0/0`, contract_tp/fp/fn=`4670/130/9`
- java:module: recall=`1.000000`, precision=`0.831818`, tp/fp/fn=`183/37/0`
- java:class: recall=`0.998653`, precision=`1.000000`, tp/fp/fn=`4448/0/6`
- java:method: recall=`0.928571`, precision=`0.295455`, tp/fp/fn=`39/93/3`

Expanded Proxy Alignment by language:kind
- java:module: strict_p/r=`0.831818`/`1.000000`, expanded_p/r=`0.831818`/`1.000000`
- java:class: strict_p/r=`1.000000`/`0.998653`, expanded_p/r=`1.000000`/`0.998653`
- java:method: strict_p/r=`0.295455`/`0.928571`, expanded_p/r=`0.318182`/`0.256098`

Strict vs Expanded delta by kind (top-5 worst recall delta)
- java:method: delta_recall=`0.672474`, delta_precision=`-0.022727`
- java:module: delta_recall=`0.000000`, delta_precision=`0.000000`
- java:class: delta_recall=`0.000000`, delta_precision=`0.000000`

## Independent Strict Contract Diagnostics

- strict_contract.accepted_by_provenance: `{'import_narrowed': 34, 'module_scoped': 28}`
- strict_contract.dropped_by_reason: `{'no_candidates': 1900, 'unique_without_provenance': 1787, 'ambiguous_multiple_in_scope_candidates': 7, 'ambiguous_no_in_scope_candidate': 163}`
- strict_contract.candidate_count_histogram: `{'0': 1900, '1': 1815, '2': 70, '24': 35, '22': 3, '4': 9, '9': 6, '6': 23, '8': 7, '12': 13, '5': 8, '53': 5, '7': 7, '10': 3, '13': 1, '3': 7, '81': 4, '20': 3}`

## Call Resolution Diagnostics

- call_form.direct: tp=`4670`, fn=`9`, recall=`0.998077`
- call_form.member: tp=`0`, fn=`0`, recall=`None`
- mismatch_attribution.core_missed_resolution: `0`
- mismatch_attribution.core_overresolution: `3620`
- mismatch_attribution.normalization_contract_mismatch: `0`
- mismatch_attribution.independent_overprojection: `3497`
- resolution.accepted_by_provenance: `{'exact_qname': 176, 'import_narrowed': 31, 'module_scoped': 4}`
- resolution.dropped_by_reason: `{'ambiguous_multiple_in_scope_candidates': 10, 'ambiguous_no_in_scope_candidate': 86, 'unique_without_provenance': 57, 'no_candidates': 17}`
- resolution.candidate_count_histogram: `{'1': 237, '6': 23, '3': 19, '8': 17, '83': 5, '2': 18, '9': 4, '0': 17, '33': 7, '57': 5, '5': 4, '7': 4, '13': 5, '4': 5, '10': 1, '12': 2, '11': 2, '25': 2, '20': 3, '15': 1}`
- resolution.record_drops: `{'duplicate_caller_record': 53, 'no_resolved_callees': 18}`
- resolution.java:method: accepted=`{'exact_qname': 176, 'import_narrowed': 31, 'module_scoped': 4}`, dropped=`{'ambiguous_multiple_in_scope_candidates': 10, 'ambiguous_no_in_scope_candidate': 86, 'unique_without_provenance': 57, 'no_candidates': 17}`

## Class Mapping Reliability

- class_rows_parse_ok_with_methods: `151`
- class_rows_unreliable_mapping: `0`
- class_rows_scored: `151`
- unreliable_mapping_rate: `0.000000`

## Out-of-Contract Distribution

- call: `1936`

Breakdown by `edge_type::language::reason`:
- call::java::in_repo_unresolved: `1936`

Note: `enrichment_edges` includes only in-repo out-of-contract edges (unresolved, dynamic, standard-call filtered); external edges are excluded.

## Independent Parser Coverage & Totals

- coverage.java: files_parsed/files_total=`265/265` (1.000000)
- raw_call_edges: `68763`
- raw_import_edges: `2449`
- normalized_call_edges: `68763`
- normalized_import_edges: `2449`
- contract_truth_edges: `4679`
- enrichment_edges: `122`
- enriched_truth_edges: `4801`
- expanded_high_conf_edges: `4801`
- expanded_full_edges: `4801`
- excluded_out_of_scope_edges: `3257`
- included_limitation_edges: `1936`

## Core Metrics

- static_contract_recall: `0.998077`
- static_overreach_rate: `0.027083`
- overreach_count: `130`
- reducer_edge_total: `4802`

## Action Priority Board

- [high] core_analysis::method_precision_gap evidence=`{'method_precision': 0.29545454545454547}`
- [medium] core_analysis::reasoning_reliability_low evidence=`{'reasoning_structural_reliability': 0.28761061946902655}`

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

