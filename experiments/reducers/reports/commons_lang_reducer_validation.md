# SCIONA Reducer Validation Report

## Executive Summary

- repo=commons_lang
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
- gate_member_call_recall_min: `None`
- gate_equal_contract_metrics_when_exact: `True`

## Internal Integrity (Hard Gates)

- valid: `True`
- static_projection_precision: `1.000000`
- static_projection_recall: `1.000000`
- parser_stability_score: `1.000000`

## Contract Alignment (Strict)

- static_contract_precision: `0.980898`
- static_contract_recall: `0.991244`
- static_overreach_rate: `0.019102`
- static_divergence_index: `0.027528`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.9723796033994334, 0.9859913793103449], 'recall_ci95': [0.986969111969112, 0.9942229924898902], 'n': 497}, 'method': {'precision_ci95': [0.6633663366336634, 0.8238095238095238], 'recall_ci95': [0.7272727272727273, 0.8588235294117647], 'n': 167}}`

## Expanded Truth Alignment (Diagnostic)

- reducer_vs_enriched_truth_precision: `0.981686`
- reducer_vs_enriched_truth_recall: `0.973823`
- db_vs_enriched_truth_precision: `0.981686`
- db_vs_enriched_truth_recall: `0.973823`
- reducer_vs_enriched_truth_divergence_index: `0.043553`
- inclusion_policy: `{'base': 'contract_truth_edges + limitation_edges', 'scope_exclusions': ['standard_call', 'external'], 'limitation_focus': ['dynamic', 'in_repo_unresolved', 'relative_unresolved'], 'confidence_tiers': {'high': ['in_repo_unresolved'], 'low': ['dynamic', 'relative_unresolved']}, 'notes': 'Expanded truth is diagnostic-only and non-gating.'}`
- tier.high_conf: reducer_p/r=`0.981686`/`0.973823`, db_p/r=`0.981686`/`0.973823`, divergence=`0.043553`
- tier.full: reducer_p/r=`0.981686`/`0.973823`, db_p/r=`0.981686`/`0.973823`, divergence=`0.043553`
- tier_edge_counts: `{'high_conf_edges': 5119, 'full_edges': 5119}`
- scope_split_counts: `{'excluded_out_of_scope_edges': 5213, 'included_limitation_edges': 239, 'excluded_out_of_scope_by_reason': {'external': 5199, 'standard_call': 14}, 'included_limitation_by_reason': {'in_repo_unresolved': 239}}`
Reason-level expanded recall:
- reason.in_repo_unresolved: reducer_recall=`0.042553`, db_recall=`0.042553`, reducer_tp/fn=`4/90`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.9750404437254448, 0.9869230769230769], 'recall_ci95': [0.963524500109866, 0.9808522620611977], 'n': 497}}`

## Prompt Reliability (Heuristic Diagnostics)

- navigation_structural_reliability: `0.822222`
- reasoning_structural_reliability: `0.617932`
- coupling_stability_index: `0.980898`
- prompt_reliability_version: `v1`
- weights: `{'navigation': {'fp_weight': 1.0, 'fn_weight': 1.0}, 'reasoning': {'fp_weight': 1.0, 'fn_weight': 1.2}}`
- component_contributions: `{'navigation': {'tp': 222, 'fp': 48, 'fn': 0, 'penalty_fp': 48.0, 'penalty_fn': 0.0, 'denominator': 270.0}, 'reasoning': {'tp': 153, 'fp': 49, 'fn': 38, 'penalty_fp': 49.0, 'penalty_fn': 45.6, 'denominator': 247.6}}`
- enrichment_noise_ratio: `0.018363`

## Language Breakdown

- java: sampled_nodes=`500`, population_nodes=`9883`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`0.980898`/`0.991244`, expanded_p/r=`0.981686`/`0.973823`, contract_overreach=`0.019102`, projection_tp/fp/fn=`5081/0/0`, contract_tp/fp/fn=`4981/97/44`
- java:module: recall=`1.000000`, precision=`0.822222`, tp/fp/fn=`222/48/0`
- java:class: recall=`0.998699`, precision=`1.000000`, tp/fp/fn=`4606/0/6`
- java:method: recall=`0.801047`, precision=`0.757426`, tp/fp/fn=`153/49/38`

Expanded Alignment by language:kind
- java:module: strict_p/r=`0.822222`/`1.000000`, expanded_p/r=`0.822222`/`1.000000`
- java:class: strict_p/r=`1.000000`/`0.998699`, expanded_p/r=`1.000000`/`0.998699`
- java:method: strict_p/r=`0.757426`/`0.801047`, expanded_p/r=`0.777228`/`0.550877`

Strict vs Expanded delta by kind (top-5 worst recall delta)
- java:method: delta_recall=`0.250170`, delta_precision=`-0.019802`
- java:module: delta_recall=`0.000000`, delta_precision=`0.000000`
- java:class: delta_recall=`0.000000`, delta_precision=`0.000000`

## Call Resolution Diagnostics

- call_form.direct: tp=`4981`, fn=`44`, recall=`0.991244`
- call_form.member: tp=`0`, fn=`0`, recall=`None`
- mismatch_attribution.core_missed_resolution: `0`
- mismatch_attribution.core_overresolution: `497`
- mismatch_attribution.normalization_contract_mismatch: `0`
- mismatch_attribution.independent_overprojection: `441`

## Out-of-Contract Distribution

- call: `239`

Breakdown by `edge_type::language::reason`:
- call::java::in_repo_unresolved: `239`

Note: `enrichment_edges` includes only in-repo out-of-contract edges (unresolved, dynamic, standard-call filtered); external edges are excluded.

## Independent Parser Coverage & Totals

- coverage.java: files_parsed/files_total=`262/262` (1.000000)
- raw_call_edges: `71229`
- raw_import_edges: `2571`
- normalized_call_edges: `71229`
- normalized_import_edges: `2571`
- contract_truth_edges: `5025`
- enrichment_edges: `94`
- enriched_truth_edges: `5119`
- expanded_high_conf_edges: `5119`
- expanded_full_edges: `5119`
- excluded_out_of_scope_edges: `5213`
- included_limitation_edges: `239`

## Core Metrics

- static_contract_recall: `0.991244`
- static_overreach_rate: `0.019102`
- overreach_count: `97`
- reducer_edge_total: `5081`

## Action Priority Board

- [high] core_analysis::method_recall_gap evidence=`{'method_recall': 0.8010471204188482}`
- [high] core_analysis::method_precision_gap evidence=`{'method_precision': 0.7574257425742574}`
- [medium] core_analysis::reasoning_reliability_low evidence=`{'reasoning_structural_reliability': 0.6179321486268174}`

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

