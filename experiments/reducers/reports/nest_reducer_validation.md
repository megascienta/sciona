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

- static_contract_precision: `0.947980`
- static_contract_recall: `0.976625`
- static_overreach_rate: `0.052020`
- static_divergence_index: `0.073052`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.925826028320971, 0.965711361310133], 'recall_ci95': [0.9658508821855435, 0.9844886088221038], 'n': 500}, 'method': {'precision_ci95': [0.7352941176470589, 0.903954802259887], 'recall_ci95': [0.7718120805369127, 0.880184331797235], 'n': 125}}`

## Expanded Truth Alignment (Diagnostic)

- reducer_vs_enriched_truth_precision: `0.954621`
- reducer_vs_enriched_truth_recall: `0.905987`
- db_vs_enriched_truth_precision: `0.954621`
- db_vs_enriched_truth_recall: `0.905987`
- reducer_vs_enriched_truth_divergence_index: `0.131420`
- inclusion_policy: `{'base': 'contract_truth_edges + limitation_edges', 'scope_exclusions': ['standard_call', 'external'], 'limitation_focus': ['dynamic', 'in_repo_unresolved', 'relative_unresolved'], 'confidence_tiers': {'high': ['in_repo_unresolved'], 'low': ['dynamic', 'relative_unresolved']}, 'notes': 'Expanded truth is diagnostic-only and non-gating.'}`
- tier.high_conf: reducer_p/r=`0.954621`/`0.916091`, db_p/r=`0.954621`/`0.916091`, divergence=`0.122137`
- tier.full: reducer_p/r=`0.954621`/`0.905987`, db_p/r=`0.954621`/`0.905987`, divergence=`0.131420`
- tier_edge_counts: `{'high_conf_edges': 1883, 'full_edges': 1904}`
- scope_split_counts: `{'excluded_out_of_scope_edges': 830, 'included_limitation_edges': 178, 'excluded_out_of_scope_by_reason': {'external': 756, 'standard_call': 74}, 'included_limitation_by_reason': {'in_repo_unresolved': 156, 'dynamic': 22}}`
Reason-level expanded recall:
- reason.dynamic: reducer_recall=`0.000000`, db_recall=`0.000000`, reducer_tp/fn=`0/21`
- reason.in_repo_unresolved: reducer_recall=`0.093023`, db_recall=`0.093023`, reducer_tp/fn=`12/117`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.9319727891156463, 0.9706780696395846], 'recall_ci95': [0.8832923832923832, 0.9256791389031266], 'n': 500}}`

## Prompt Reliability (Heuristic Diagnostics)

- navigation_structural_reliability: `0.998008`
- reasoning_structural_reliability: `0.739061`
- coupling_stability_index: `0.947980`
- prompt_reliability_version: `v1`
- weights: `{'navigation': {'fp_weight': 1.0, 'fn_weight': 1.0}, 'reasoning': {'fp_weight': 1.0, 'fn_weight': 1.2}}`
- component_contributions: `{'navigation': {'tp': 501, 'fp': 1, 'fn': 0, 'penalty_fp': 1.0, 'penalty_fn': 0.0, 'denominator': 502.0}, 'reasoning': {'tp': 277, 'fp': 51, 'fn': 39, 'penalty_fp': 51.0, 'penalty_fn': 46.8, 'denominator': 374.8}}`
- enrichment_noise_ratio: `0.078782`

## Language Breakdown

- typescript: sampled_nodes=`500`, population_nodes=`6033`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`0.947980`/`0.976625`, expanded_p/r=`0.954621`/`0.905987`, contract_overreach=`0.052020`, projection_tp/fp/fn=`1807/0/0`, contract_tp/fp/fn=`1713/94/41`
- typescript:module: recall=`1.000000`, precision=`0.998008`, tp/fp/fn=`501/1/0`
- typescript:class: recall=`0.997866`, precision=`0.957011`, tp/fp/fn=`935/42/2`
- typescript:function: recall=`0.938462`, precision=`0.871429`, tp/fp/fn=`122/18/8`
- typescript:method: recall=`0.833333`, precision=`0.824468`, tp/fp/fn=`155/33/31`

Expanded Alignment by language:kind
- typescript:module: strict_p/r=`0.998008`/`1.000000`, expanded_p/r=`0.998008`/`1.000000`
- typescript:class: strict_p/r=`0.957011`/`0.997866`, expanded_p/r=`0.957011`/`0.997866`
- typescript:function: strict_p/r=`0.871429`/`0.938462`, expanded_p/r=`0.878571`/`0.549107`
- typescript:method: strict_p/r=`0.824468`/`0.833333`, expanded_p/r=`0.882979`/`0.685950`

Strict vs Expanded delta by kind (top-5 worst recall delta)
- typescript:function: delta_recall=`0.389354`, delta_precision=`-0.007143`
- typescript:method: delta_recall=`0.147383`, delta_precision=`-0.058511`
- typescript:module: delta_recall=`0.000000`, delta_precision=`0.000000`
- typescript:class: delta_recall=`0.000000`, delta_precision=`0.000000`

## Call Resolution Diagnostics

- call_form.direct: tp=`1548`, fn=`18`, recall=`0.988506`
- call_form.member: tp=`167`, fn=`21`, recall=`0.888298`
- mismatch_attribution.core_missed_resolution: `0`
- mismatch_attribution.core_overresolution: `111`
- mismatch_attribution.normalization_contract_mismatch: `0`
- mismatch_attribution.independent_overprojection: `55`

## Out-of-Contract Distribution

- call: `178`

Breakdown by `edge_type::language::reason`:
- call::typescript::dynamic: `22`
- call::typescript::in_repo_unresolved: `156`

Note: `enrichment_edges` includes only in-repo out-of-contract edges (unresolved, dynamic, standard-call filtered); external edges are excluded.

## Independent Parser Coverage & Totals

- coverage.typescript: files_parsed/files_total=`357/357` (1.000000)
- raw_call_edges: `17578`
- raw_import_edges: `2040`
- normalized_call_edges: `17578`
- normalized_import_edges: `2040`
- contract_truth_edges: `1754`
- enrichment_edges: `150`
- enriched_truth_edges: `1904`
- expanded_high_conf_edges: `1883`
- expanded_full_edges: `1904`
- excluded_out_of_scope_edges: `830`
- included_limitation_edges: `178`

## Core Metrics

- static_contract_recall: `0.976625`
- static_overreach_rate: `0.052020`
- overreach_count: `94`
- reducer_edge_total: `1807`

## Action Priority Board

- [high] core_analysis::method_recall_gap evidence=`{'method_recall': 0.8333333333333334}`
- [high] core_analysis::method_precision_gap evidence=`{'method_precision': 0.824468085106383}`
- [high] core_analysis::strict_overreach_elevated evidence=`{'strict_overreach_rate': 0.05201992252351965}`
- [medium] validation_workflow::strict_to_expanded_recall_drop evidence=`{'strict_recall': 0.9766248574686431, 'expanded_full_recall': 0.9059873949579832, 'delta': 0.07063746251065994}`

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

