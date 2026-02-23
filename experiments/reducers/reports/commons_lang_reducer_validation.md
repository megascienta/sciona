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
- gate_contract_recall_min: `True`
- gate_overreach_rate_max: `True`
- gate_member_call_recall_min: `None`
- gate_equal_contract_metrics_when_exact: `True`

## Internal Integrity (Hard Gates)

- valid: `True`
- static_projection_precision: `1.000000`
- static_projection_recall: `1.000000`
- parser_stability_score: `1.000000`

## Contract Alignment (Strict Proxy)

- static_contract_precision: `0.980376`
- static_contract_recall: `0.972861`
- static_overreach_rate: `0.019624`
- static_divergence_index: `0.045722`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.9733042767638246, 0.9855229822656533], 'recall_ci95': [0.9602495955627456, 0.9814514676751306], 'n': 498}, 'method': {'precision_ci95': [0.5533333333333333, 0.7518248175182481], 'recall_ci95': [0.3614457831325301, 0.518918918918919], 'n': 167}}`

## Expanded Proxy Alignment (Diagnostic)

- reducer_vs_enriched_truth_precision: `0.980585`
- reducer_vs_enriched_truth_recall: `0.960925`
- db_vs_enriched_truth_precision: `0.980585`
- db_vs_enriched_truth_recall: `0.960925`
- reducer_vs_enriched_truth_divergence_index: `0.057017`
- inclusion_policy: `{'base': 'contract_truth_edges + limitation_edges', 'scope_exclusions': ['standard_call', 'external'], 'limitation_focus': ['dynamic', 'in_repo_unresolved', 'relative_unresolved'], 'confidence_tiers': {'high': ['in_repo_unresolved'], 'low': ['dynamic', 'relative_unresolved']}, 'notes': 'Expanded truth is diagnostic-only and non-gating.'}`
- tier.high_conf: reducer_p/r=`0.980585`/`0.960925`, db_p/r=`0.980585`/`0.960925`, divergence=`0.057017`
- tier.full: reducer_p/r=`0.980585`/`0.960925`, db_p/r=`0.980585`/`0.960925`, divergence=`0.057017`
- tier_edge_counts: `{'high_conf_edges': 4888, 'full_edges': 4888}`
- scope_split_counts: `{'excluded_out_of_scope_edges': 4756, 'included_limitation_edges': 106, 'excluded_out_of_scope_by_reason': {'external': 4747, 'standard_call': 9}, 'included_limitation_by_reason': {'in_repo_unresolved': 106}}`
Reason-level expanded proxy recall:
- reason.in_repo_unresolved: reducer_recall=`0.016393`, db_recall=`0.016393`, reducer_tp/fn=`1/60`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.9719874426467037, 0.9875067897881586], 'recall_ci95': [0.9434315100514259, 0.9745810581811335], 'n': 498}}`

## Prompt Reliability (Heuristic Diagnostics)

- navigation_structural_reliability: `0.825203`
- reasoning_structural_reliability: `0.323232`
- coupling_stability_index: `0.980376`
- prompt_reliability_version: `v1`
- weights: `{'navigation': {'fp_weight': 1.0, 'fn_weight': 1.0}, 'reasoning': {'fp_weight': 1.0, 'fn_weight': 1.2}}`
- component_contributions: `{'navigation': {'tp': 203, 'fp': 43, 'fn': 0, 'penalty_fp': 43.0, 'penalty_fn': 0.0, 'denominator': 246.0}, 'reasoning': {'tp': 96, 'fp': 51, 'fn': 125, 'penalty_fp': 51.0, 'penalty_fn': 150.0, 'denominator': 297.0}}`
- enrichment_noise_ratio: `0.012480`

## Language Breakdown

- java: sampled_nodes=`500`, population_nodes=`9883`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`0.980376`/`0.972861`, expanded_p/r=`0.980585`/`0.960925`, contract_overreach=`0.019624`, projection_tp/fp/fn=`4792/0/0`, contract_tp/fp/fn=`4696/94/131`
- java:module: recall=`1.000000`, precision=`0.825203`, tp/fp/fn=`203/43/0`
- java:class: recall=`0.998637`, precision=`1.000000`, tp/fp/fn=`4397/0/6`
- java:method: recall=`0.434389`, precision=`0.653061`, tp/fp/fn=`96/51/125`

Expanded Proxy Alignment by language:kind
- java:module: strict_p/r=`0.825203`/`1.000000`, expanded_p/r=`0.825203`/`1.000000`
- java:class: strict_p/r=`1.000000`/`0.998637`, expanded_p/r=`1.000000`/`0.998637`
- java:method: strict_p/r=`0.653061`/`0.434389`, expanded_p/r=`0.659864`/`0.343972`

Strict vs Expanded delta by kind (top-5 worst recall delta)
- java:method: delta_recall=`0.090418`, delta_precision=`-0.006803`
- java:module: delta_recall=`0.000000`, delta_precision=`0.000000`
- java:class: delta_recall=`0.000000`, delta_precision=`0.000000`

## Call Resolution Diagnostics

- call_form.direct: tp=`4696`, fn=`131`, recall=`0.972861`
- call_form.member: tp=`0`, fn=`0`, recall=`None`
- mismatch_attribution.core_missed_resolution: `0`
- mismatch_attribution.core_overresolution: `656`
- mismatch_attribution.normalization_contract_mismatch: `0`
- mismatch_attribution.independent_overprojection: `691`

## Out-of-Contract Distribution

- call: `106`

Breakdown by `edge_type::language::reason`:
- call::java::in_repo_unresolved: `106`

Note: `enrichment_edges` includes only in-repo out-of-contract edges (unresolved, dynamic, standard-call filtered); external edges are excluded.

## Independent Parser Coverage & Totals

- coverage.java: files_parsed/files_total=`269/269` (1.000000)
- raw_call_edges: `68828`
- raw_import_edges: `2474`
- normalized_call_edges: `68828`
- normalized_import_edges: `2474`
- contract_truth_edges: `4827`
- enrichment_edges: `61`
- enriched_truth_edges: `4888`
- expanded_high_conf_edges: `4888`
- expanded_full_edges: `4888`
- excluded_out_of_scope_edges: `4756`
- included_limitation_edges: `106`

## Core Metrics

- static_contract_recall: `0.972861`
- static_overreach_rate: `0.019624`
- overreach_count: `94`
- reducer_edge_total: `4792`

## Action Priority Board

- [high] core_analysis::method_recall_gap evidence=`{'method_recall': 0.4343891402714932}`
- [high] core_analysis::method_precision_gap evidence=`{'method_precision': 0.6530612244897959}`
- [medium] core_analysis::reasoning_reliability_low evidence=`{'reasoning_structural_reliability': 0.32323232323232326}`

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

