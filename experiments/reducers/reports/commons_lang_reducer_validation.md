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

- static_contract_precision: `0.984521`
- static_contract_recall: `0.990371`
- static_overreach_rate: `0.015479`
- static_divergence_index: `0.024813`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.9781089892873778, 0.9889030380207385], 'recall_ci95': [0.9857487922705314, 0.9936080740117746], 'n': 499}, 'method': {'precision_ci95': [0.7339449541284404, 0.8663594470046083], 'recall_ci95': [0.7453703703703703, 0.8682926829268293], 'n': 166}}`

## Expanded Truth Alignment (Diagnostic)

- reducer_vs_enriched_truth_precision: `0.984929`
- reducer_vs_enriched_truth_recall: `0.970695`
- db_vs_enriched_truth_precision: `0.984929`
- db_vs_enriched_truth_recall: `0.970695`
- reducer_vs_enriched_truth_divergence_index: `0.043513`
- inclusion_policy: `{'base': 'contract_truth_edges + limitation_edges', 'scope_exclusions': ['standard_call', 'external'], 'limitation_focus': ['dynamic', 'in_repo_unresolved', 'relative_unresolved'], 'confidence_tiers': {'high': ['in_repo_unresolved'], 'low': ['dynamic', 'relative_unresolved']}, 'notes': 'Expanded truth is diagnostic-only and non-gating.'}`
- tier.high_conf: reducer_p/r=`0.984929`/`0.970695`, db_p/r=`0.984929`/`0.970695`, divergence=`0.043513`
- tier.full: reducer_p/r=`0.984929`/`0.970695`, db_p/r=`0.984929`/`0.970695`, divergence=`0.043513`
- tier_edge_counts: `{'high_conf_edges': 4982, 'full_edges': 4982}`
- scope_split_counts: `{'excluded_out_of_scope_edges': 5029, 'included_limitation_edges': 260, 'excluded_out_of_scope_by_reason': {'external': 4997, 'standard_call': 32}, 'included_limitation_by_reason': {'in_repo_unresolved': 260}}`
Reason-level expanded recall:
- reason.in_repo_unresolved: reducer_recall=`0.019802`, db_recall=`0.019802`, reducer_tp/fn=`2/99`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.9787735849056604, 0.9894924309884239], 'recall_ci95': [0.9600084192801516, 0.9799382716049383], 'n': 499}}`

## Prompt Reliability (Heuristic Diagnostics)

- navigation_structural_reliability: `0.847458`
- reasoning_structural_reliability: `0.657051`
- coupling_stability_index: `0.984521`
- prompt_reliability_version: `v1`
- weights: `{'navigation': {'fp_weight': 1.0, 'fn_weight': 1.0}, 'reasoning': {'fp_weight': 1.0, 'fn_weight': 1.2}}`
- component_contributions: `{'navigation': {'tp': 200, 'fp': 36, 'fn': 0, 'penalty_fp': 36.0, 'penalty_fn': 0.0, 'denominator': 236.0}, 'reasoning': {'tp': 164, 'fp': 40, 'fn': 38, 'penalty_fp': 40.0, 'penalty_fn': 45.6, 'denominator': 249.6}}`
- enrichment_noise_ratio: `0.020273`

## Language Breakdown

- java: sampled_nodes=`500`, population_nodes=`9722`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`0.984521`/`0.990371`, expanded_p/r=`0.984929`/`0.970695`, contract_overreach=`0.015479`, projection_tp/fp/fn=`4913/0/0`, contract_tp/fp/fn=`4834/76/47`
- java:module: recall=`1.000000`, precision=`0.847458`, tp/fp/fn=`200/36/0`
- java:class: recall=`0.997991`, precision=`1.000000`, tp/fp/fn=`4470/0/9`
- java:method: recall=`0.811881`, precision=`0.803922`, tp/fp/fn=`164/40/38`

Expanded Alignment by language:kind
- java:module: strict_p/r=`0.847458`/`1.000000`, expanded_p/r=`0.847458`/`1.000000`
- java:class: strict_p/r=`1.000000`/`0.997991`, expanded_p/r=`1.000000`/`0.997991`
- java:method: strict_p/r=`0.803922`/`0.811881`, expanded_p/r=`0.813725`/`0.547855`

Strict vs Expanded delta by kind (top-5 worst recall delta)
- java:method: delta_recall=`0.264026`, delta_precision=`-0.009804`
- java:module: delta_recall=`0.000000`, delta_precision=`0.000000`
- java:class: delta_recall=`0.000000`, delta_precision=`0.000000`

## Call Resolution Diagnostics

- call_form.direct: tp=`4834`, fn=`47`, recall=`0.990371`
- call_form.member: tp=`0`, fn=`0`, recall=`None`
- mismatch_attribution.core_missed_resolution: `0`
- mismatch_attribution.core_overresolution: `1242`
- mismatch_attribution.normalization_contract_mismatch: `0`
- mismatch_attribution.independent_overprojection: `1210`

## Out-of-Contract Distribution

- call: `260`

Breakdown by `edge_type::language::reason`:
- call::java::in_repo_unresolved: `260`

Note: `enrichment_edges` includes only in-repo out-of-contract edges (unresolved, dynamic, standard-call filtered); external edges are excluded.

## Independent Parser Coverage & Totals

- coverage.java: files_parsed/files_total=`263/263` (1.000000)
- raw_call_edges: `70293`
- raw_import_edges: `2537`
- normalized_call_edges: `70293`
- normalized_import_edges: `2537`
- contract_truth_edges: `4881`
- enrichment_edges: `101`
- enriched_truth_edges: `4982`
- expanded_high_conf_edges: `4982`
- expanded_full_edges: `4982`
- excluded_out_of_scope_edges: `5029`
- included_limitation_edges: `260`

## Core Metrics

- static_contract_recall: `0.990371`
- static_overreach_rate: `0.015479`
- overreach_count: `76`
- reducer_edge_total: `4913`

## Action Priority Board

- [high] core_analysis::method_recall_gap evidence=`{'method_recall': 0.8118811881188119}`
- [high] core_analysis::method_precision_gap evidence=`{'method_precision': 0.803921568627451}`
- [medium] core_analysis::reasoning_reliability_low evidence=`{'reasoning_structural_reliability': 0.657051282051282}`

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

