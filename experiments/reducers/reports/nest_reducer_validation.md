# SCIONA Reducer Validation Report

## Executive Summary

- repo=nest
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

- static_contract_precision: `0.947046`
- static_contract_recall: `0.977560`
- static_overreach_rate: `0.052954`
- static_divergence_index: `0.073104`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.9247743229689067, 0.9649947753396029], 'recall_ci95': [0.9682642487046632, 0.9863874345549738], 'n': 500}, 'method': {'precision_ci95': [0.7311827956989247, 0.8524590163934426], 'recall_ci95': [0.7663043478260869, 0.8918918918918919], 'n': 125}}`

## Expanded Truth Alignment (Diagnostic)

- reducer_vs_enriched_truth_precision: `0.955964`
- reducer_vs_enriched_truth_recall: `0.911265`
- db_vs_enriched_truth_precision: `0.955964`
- db_vs_enriched_truth_recall: `0.911265`
- reducer_vs_enriched_truth_divergence_index: `0.125446`
- inclusion_policy: `{'base': 'contract_truth_edges + limitation_edges', 'scope_exclusions': ['standard_call', 'external'], 'limitation_focus': ['dynamic', 'in_repo_unresolved', 'relative_unresolved'], 'confidence_tiers': {'high': ['in_repo_unresolved'], 'low': ['dynamic', 'relative_unresolved']}, 'notes': 'Expanded truth is diagnostic-only and non-gating.'}`
- tier.high_conf: reducer_p/r=`0.955964`/`0.920558`, db_p/r=`0.955964`/`0.920558`, divergence=`0.116890`
- tier.full: reducer_p/r=`0.955964`/`0.911265`, db_p/r=`0.955964`/`0.911265`, divergence=`0.125446`
- tier_edge_counts: `{'high_conf_edges': 1863, 'full_edges': 1882}`
- scope_split_counts: `{'excluded_out_of_scope_edges': 839, 'included_limitation_edges': 170, 'excluded_out_of_scope_by_reason': {'external': 772, 'standard_call': 67}, 'included_limitation_by_reason': {'in_repo_unresolved': 150, 'dynamic': 20}}`
Reason-level expanded recall:
- reason.dynamic: reducer_recall=`0.000000`, db_recall=`0.000000`, reducer_tp/fn=`0/19`
- reason.in_repo_unresolved: reducer_recall=`0.128000`, db_recall=`0.128000`, reducer_tp/fn=`16/109`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.9333991119881598, 0.971106412966878], 'recall_ci95': [0.8884416331224841, 0.9305423406279734], 'n': 500}}`

## Prompt Reliability (Heuristic Diagnostics)

- navigation_structural_reliability: `0.998008`
- reasoning_structural_reliability: `0.725233`
- coupling_stability_index: `0.947046`
- prompt_reliability_version: `v1`
- weights: `{'navigation': {'fp_weight': 1.0, 'fn_weight': 1.0}, 'reasoning': {'fp_weight': 1.0, 'fn_weight': 1.2}}`
- component_contributions: `{'navigation': {'tp': 501, 'fp': 1, 'fn': 0, 'penalty_fp': 1.0, 'penalty_fn': 0.0, 'denominator': 502.0}, 'reasoning': {'tp': 265, 'fp': 56, 'fn': 37, 'penalty_fp': 56.0, 'penalty_fn': 44.4, 'denominator': 365.4}}`
- enrichment_noise_ratio: `0.076514`

## Language Breakdown

- typescript: sampled_nodes=`500`, population_nodes=`6033`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`0.947046`/`0.977560`, expanded_p/r=`0.955964`/`0.911265`, contract_overreach=`0.052954`, projection_tp/fp/fn=`1794/0/0`, contract_tp/fp/fn=`1699/95/39`
- typescript:module: recall=`1.000000`, precision=`0.998008`, tp/fp/fn=`501/1/0`
- typescript:class: recall=`0.997861`, precision=`0.960865`, tp/fp/fn=`933/38/2`
- typescript:function: recall=`0.937984`, precision=`0.864286`, tp/fp/fn=`121/19/8`
- typescript:method: recall=`0.832370`, precision=`0.795580`, tp/fp/fn=`144/37/29`

Expanded Alignment by language:kind
- typescript:module: strict_p/r=`0.998008`/`1.000000`, expanded_p/r=`0.998008`/`1.000000`
- typescript:class: strict_p/r=`0.960865`/`0.997861`, expanded_p/r=`0.960865`/`0.997861`
- typescript:function: strict_p/r=`0.864286`/`0.937984`, expanded_p/r=`0.871429`/`0.547085`
- typescript:method: strict_p/r=`0.795580`/`0.832370`, expanded_p/r=`0.878453`/`0.713004`

Strict vs Expanded delta by kind (top-5 worst recall delta)
- typescript:function: delta_recall=`0.390899`, delta_precision=`-0.007143`
- typescript:method: delta_recall=`0.119365`, delta_precision=`-0.082873`
- typescript:module: delta_recall=`0.000000`, delta_precision=`0.000000`
- typescript:class: delta_recall=`0.000000`, delta_precision=`0.000000`

## Call Resolution Diagnostics

- call_form.direct: tp=`1542`, fn=`19`, recall=`0.987828`
- call_form.member: tp=`158`, fn=`19`, recall=`0.892655`
- mismatch_attribution.core_missed_resolution: `0`
- mismatch_attribution.core_overresolution: `125`
- mismatch_attribution.normalization_contract_mismatch: `0`
- mismatch_attribution.independent_overprojection: `67`

## Out-of-Contract Distribution

- call: `170`

Breakdown by `edge_type::language::reason`:
- call::typescript::dynamic: `20`
- call::typescript::in_repo_unresolved: `150`

Note: `enrichment_edges` includes only in-repo out-of-contract edges (unresolved, dynamic, standard-call filtered); external edges are excluded.

## Independent Parser Coverage & Totals

- coverage.typescript: files_parsed/files_total=`348/348` (1.000000)
- raw_call_edges: `17353`
- raw_import_edges: `1973`
- normalized_call_edges: `17353`
- normalized_import_edges: `1973`
- contract_truth_edges: `1738`
- enrichment_edges: `144`
- enriched_truth_edges: `1882`
- expanded_high_conf_edges: `1863`
- expanded_full_edges: `1882`
- excluded_out_of_scope_edges: `839`
- included_limitation_edges: `170`

## Core Metrics

- static_contract_recall: `0.977560`
- static_overreach_rate: `0.052954`
- overreach_count: `95`
- reducer_edge_total: `1794`

## Action Priority Board

- [high] core_analysis::method_recall_gap evidence=`{'method_recall': 0.8323699421965318}`
- [high] core_analysis::method_precision_gap evidence=`{'method_precision': 0.7955801104972375}`
- [high] core_analysis::strict_overreach_elevated evidence=`{'strict_overreach_rate': 0.052954292084726864}`
- [medium] validation_workflow::strict_to_expanded_recall_drop evidence=`{'strict_recall': 0.977560414269275, 'expanded_full_recall': 0.9112646121147715, 'delta': 0.06629580215450348}`

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

