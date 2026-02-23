# SCIONA Reducer Validation Report

## Executive Summary

- repo=OpenLineage
- sampled_nodes=500
- invariants_passed=True

## Run Verdict

- passed: `True`
- hard_passed: `True`
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
- gate_overreach_rate_max: `False`
- gate_member_call_recall_min: `False`
- gate_equal_contract_metrics_when_exact: `True`
- diagnostic_failure: contract recall quality gate failed
- diagnostic_failure: overreach-rate quality gate failed
- diagnostic_failure: member-call recall quality gate failed

## Internal Integrity (Hard Gates)

- valid: `True`
- static_projection_precision: `1.000000`
- static_projection_recall: `1.000000`
- parser_stability_score: `1.000000`

## Contract Alignment (Strict)

- static_contract_precision: `0.874022`
- static_contract_recall: `0.949023`
- static_overreach_rate: `0.125978`
- static_divergence_index: `0.165172`

## Expanded Truth Alignment (Diagnostic)

- reducer_vs_enriched_truth_precision: `0.877934`
- reducer_vs_enriched_truth_recall: `0.887658`
- db_vs_enriched_truth_precision: `0.877934`
- db_vs_enriched_truth_recall: `0.887658`
- reducer_vs_enriched_truth_divergence_index: `0.209859`
- inclusion_policy: `{'base': 'contract_truth_edges + limitation_edges', 'scope_exclusions': ['standard_call', 'external'], 'limitation_focus': ['dynamic', 'in_repo_unresolved', 'relative_unresolved'], 'confidence_tiers': {'high': ['in_repo_unresolved'], 'low': ['dynamic', 'relative_unresolved']}, 'notes': 'Expanded truth is diagnostic-only and non-gating.'}`
- tier.high_conf: reducer_p/r=`0.877934`/`0.888361`, db_p/r=`0.877934`/`0.888361`, divergence=`0.209302`
- tier.full: reducer_p/r=`0.877934`/`0.887658`, db_p/r=`0.877934`/`0.887658`, divergence=`0.209859`
- tier_edge_counts: `{'high_conf_edges': 1263, 'full_edges': 1264}`
- scope_split_counts: `{'excluded_out_of_scope_edges': 4317, 'included_limitation_edges': 179, 'excluded_out_of_scope_by_reason': {'external': 4201, 'standard_call': 116}, 'included_limitation_by_reason': {'in_repo_unresolved': 178, 'dynamic': 1}}`

## Prompt Reliability (Heuristic Diagnostics)

- navigation_structural_reliability: `0.888889`
- reasoning_structural_reliability: `0.430990`
- coupling_stability_index: `0.874022`
- prompt_reliability_version: `v1`
- weights: `{'navigation': {'fp_weight': 1.0, 'fn_weight': 1.0}, 'reasoning': {'fp_weight': 1.0, 'fn_weight': 1.2}}`
- component_contributions: `{'navigation': {'tp': 88, 'fp': 10, 'fn': 1, 'penalty_fp': 10.0, 'penalty_fn': 1.0, 'denominator': 99.0}, 'reasoning': {'tp': 168, 'fp': 151, 'fn': 59, 'penalty_fp': 151.0, 'penalty_fn': 70.8, 'denominator': 389.8}}`
- enrichment_noise_ratio: `0.068829`

## Language Breakdown

- java: sampled_nodes=`199`, population_nodes=`7166`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`0.896067`/`0.945185`, expanded_p/r=`0.903090`/`0.872456`, contract_overreach=`0.103933`, projection_tp/fp/fn=`712/0/0`, contract_tp/fp/fn=`638/74/37`
- java:module: recall=`0.987952`, precision=`0.891304`, tp/fp/fn=`82/10/1`
- java:class: recall=`1.000000`, precision=`1.000000`, tp/fp/fn=`502/0/0`
- java:method: recall=`0.600000`, precision=`0.457627`, tp/fp/fn=`54/64/36`
- python: sampled_nodes=`272`, population_nodes=`1960`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`0.845878`/`0.955466`, expanded_p/r=`0.845878`/`0.911197`, contract_overreach=`0.154122`, projection_tp/fp/fn=`558/0/0`, contract_tp/fp/fn=`472/86/22`
- python:module: recall=`None`, precision=`None`, tp/fp/fn=`0/0/0`
- python:class: recall=`1.000000`, precision=`1.000000`, tp/fp/fn=`359/0/0`
- python:function: recall=`0.813559`, precision=`0.457143`, tp/fp/fn=`48/57/11`
- python:method: recall=`0.855263`, precision=`0.691489`, tp/fp/fn=`65/29/11`
- typescript: sampled_nodes=`29`, population_nodes=`29`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`0.875000`/`0.875000`, expanded_p/r=`0.875000`/`0.777778`, contract_overreach=`0.125000`, projection_tp/fp/fn=`8/0/0`, contract_tp/fp/fn=`7/1/1`
- typescript:module: recall=`1.000000`, precision=`1.000000`, tp/fp/fn=`6/0/0`
- typescript:function: recall=`0.500000`, precision=`0.500000`, tp/fp/fn=`1/1/1`

Expanded Alignment by language:kind
- java:module: strict_p/r=`0.891304`/`0.987952`, expanded_p/r=`0.891304`/`0.987952`
- java:class: strict_p/r=`1.000000`/`1.000000`, expanded_p/r=`1.000000`/`1.000000`
- java:method: strict_p/r=`0.457627`/`0.600000`, expanded_p/r=`0.500000`/`0.388158`
- python:module: strict_p/r=`None`/`None`, expanded_p/r=`None`/`None`
- python:class: strict_p/r=`1.000000`/`1.000000`, expanded_p/r=`1.000000`/`1.000000`
- python:function: strict_p/r=`0.457143`/`0.813559`, expanded_p/r=`0.457143`/`0.657534`
- python:method: strict_p/r=`0.691489`/`0.855263`, expanded_p/r=`0.691489`/`0.755814`
- typescript:module: strict_p/r=`1.000000`/`1.000000`, expanded_p/r=`1.000000`/`1.000000`
- typescript:function: strict_p/r=`0.500000`/`0.500000`, expanded_p/r=`0.500000`/`0.333333`

Strict vs Expanded delta by kind (top-5 worst recall delta)
- java:method: delta_recall=`0.211842`, delta_precision=`-0.042373`
- typescript:function: delta_recall=`0.166667`, delta_precision=`0.000000`
- python:function: delta_recall=`0.156025`, delta_precision=`0.000000`
- python:method: delta_recall=`0.099449`, delta_precision=`0.000000`
- typescript:module: delta_recall=`0.000000`, delta_precision=`0.000000`

## Call Resolution Diagnostics

- call_form.direct: tp=`1069`, fn=`37`, recall=`0.966546`
- call_form.member: tp=`48`, fn=`23`, recall=`0.676056`
- mismatch_attribution.core_missed_resolution: `0`
- mismatch_attribution.core_overresolution: `397`
- mismatch_attribution.normalization_contract_mismatch: `0`
- mismatch_attribution.independent_overprojection: `291`

## Out-of-Contract Distribution

- call: `179`

Breakdown by `edge_type::language::reason`:
- call::java::dynamic: `1`
- call::java::in_repo_unresolved: `152`
- call::python::in_repo_unresolved: `25`
- call::typescript::in_repo_unresolved: `1`

Note: `enrichment_edges` includes only in-repo out-of-contract edges (unresolved, dynamic, standard-call filtered); external edges are excluded.

## Independent Parser Coverage & Totals

- coverage.java: files_parsed/files_total=`164/164` (1.000000)
- coverage.python: files_parsed/files_total=`121/121` (1.000000)
- coverage.typescript: files_parsed/files_total=`15/15` (1.000000)
- raw_call_edges: `25597`
- raw_import_edges: `4751`
- normalized_call_edges: `25597`
- normalized_import_edges: `4751`
- contract_truth_edges: `1177`
- enrichment_edges: `87`
- enriched_truth_edges: `1264`

## Core Metrics

- static_contract_recall: `0.949023`
- static_overreach_rate: `0.125978`
- overreach_count: `161`
- reducer_edge_total: `1278`

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

