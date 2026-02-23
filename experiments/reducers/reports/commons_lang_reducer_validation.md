# SCIONA Reducer Validation Report

## Executive Summary

- repo=commons_lang
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

## Expanded Truth Alignment (Diagnostic)

- reducer_vs_enriched_truth_precision: `0.985132`
- reducer_vs_enriched_truth_recall: `0.968562`
- db_vs_enriched_truth_precision: `0.985132`
- db_vs_enriched_truth_recall: `0.968562`
- reducer_vs_enriched_truth_divergence_index: `0.045392`
- inclusion_policy: `{'base': 'contract_truth_edges + enrichment_edges', 'include_enrichment_reasons': ['dynamic', 'in_repo_unresolved', 'relative_unresolved', 'standard_call'], 'exclude_enrichment_reasons': ['external'], 'notes': 'Enriched truth is diagnostic-only and non-gating.'}`

## Prompt Reliability (Heuristic Diagnostics)

- navigation_structural_reliability: `0.847458`
- reasoning_structural_reliability: `0.657051`
- coupling_stability_index: `0.984521`
- weights: `{'navigation': {'fp_weight': 1.0, 'fn_weight': 1.0}, 'reasoning': {'fp_weight': 1.0, 'fn_weight': 1.2}}`
- enrichment_noise_ratio: `0.022627`

## Language Breakdown

- java: sampled_nodes=`500`, population_nodes=`9722`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`0.984521`/`0.990371`, expanded_p/r=`0.985132`/`0.968562`, contract_overreach=`0.015479`, projection_tp/fp/fn=`4913/0/0`, contract_tp/fp/fn=`4834/76/47`
- java:module: recall=`1.000000`, precision=`0.847458`, tp/fp/fn=`200/36/0`
- java:class: recall=`0.997991`, precision=`1.000000`, tp/fp/fn=`4470/0/9`
- java:method: recall=`0.811881`, precision=`0.803922`, tp/fp/fn=`164/40/38`

## Call Resolution Diagnostics

- call_form.direct: tp=`4834`, fn=`47`, recall=`0.990371`
- call_form.member: tp=`0`, fn=`0`, recall=`None`
- mismatch_attribution.core_missed_resolution: `0`
- mismatch_attribution.core_overresolution: `1242`
- mismatch_attribution.normalization_contract_mismatch: `0`
- mismatch_attribution.independent_overprojection: `1210`

## Out-of-Contract Distribution

- call: `292`

Breakdown by `edge_type::language::reason`:
- call::java::in_repo_unresolved: `260`
- call::java::standard_call: `32`

Note: `enrichment_edges` includes only in-repo out-of-contract edges (unresolved, dynamic, standard-call filtered); external edges are excluded.

## Independent Parser Coverage & Totals

- coverage.java: files_parsed/files_total=`263/263` (1.000000)
- raw_call_edges: `70293`
- raw_import_edges: `2537`
- normalized_call_edges: `70293`
- normalized_import_edges: `2537`
- contract_truth_edges: `4881`
- enrichment_edges: `113`
- enriched_truth_edges: `4994`

## Core Metrics

- static_contract_recall: `0.990371`
- static_overreach_rate: `0.015479`
- overreach_count: `76`
- reducer_edge_total: `4913`

## Metric Definitions & Schema

- report_schema_version: `2026-02-23`
- enriched_alignment_precision: layer=`enrichment_practical`, source=`reducer_vs_enriched_truth`, formula=`tp / (tp + fp)`
- enriched_alignment_recall: layer=`enrichment_practical`, source=`reducer_vs_enriched_truth`, formula=`tp / (tp + fn)`
- static_contract_precision: layer=`static_contract_alignment`, source=`reducer_vs_contract_truth`, formula=`tp / (tp + fp)`
- static_contract_recall: layer=`static_contract_alignment`, source=`reducer_vs_contract_truth`, formula=`tp / (tp + fn)`
- static_overreach_rate: layer=`static_contract_alignment`, source=`reducer_vs_contract_truth`, formula=`fp / (tp + fp)`
- static_projection_precision: layer=`internal_integrity`, source=`reducer_vs_db`, formula=`tp / (tp + fp)`
- static_projection_recall: layer=`internal_integrity`, source=`reducer_vs_db`, formula=`tp / (tp + fn)`

