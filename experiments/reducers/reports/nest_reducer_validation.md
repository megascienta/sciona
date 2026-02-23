# SCIONA Reducer Validation Report

## Executive Summary

- repo=nest
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

## Expanded Truth Alignment (Diagnostic)

- reducer_vs_enriched_truth_precision: `0.957637`
- reducer_vs_enriched_truth_recall: `0.886481`
- db_vs_enriched_truth_precision: `0.957637`
- db_vs_enriched_truth_recall: `0.886481`
- reducer_vs_enriched_truth_divergence_index: `0.146971`
- inclusion_policy: `{'base': 'contract_truth_edges + enrichment_edges', 'include_enrichment_reasons': ['dynamic', 'in_repo_unresolved', 'relative_unresolved', 'standard_call'], 'exclude_enrichment_reasons': ['external'], 'notes': 'Enriched truth is diagnostic-only and non-gating.'}`

## Prompt Reliability (Heuristic Diagnostics)

- navigation_structural_reliability: `0.998008`
- reasoning_structural_reliability: `0.725233`
- coupling_stability_index: `0.947046`
- weights: `{'navigation': {'fp_weight': 1.0, 'fn_weight': 1.0}, 'reasoning': {'fp_weight': 1.0, 'fn_weight': 1.2}}`
- enrichment_noise_ratio: `0.103199`

## Language Breakdown

- typescript: sampled_nodes=`500`, population_nodes=`6033`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`0.947046`/`0.977560`, expanded_p/r=`0.957637`/`0.886481`, contract_overreach=`0.052954`, projection_tp/fp/fn=`1794/0/0`, contract_tp/fp/fn=`1699/95/39`
- typescript:module: recall=`1.000000`, precision=`0.998008`, tp/fp/fn=`501/1/0`
- typescript:class: recall=`0.997861`, precision=`0.960865`, tp/fp/fn=`933/38/2`
- typescript:function: recall=`0.937984`, precision=`0.864286`, tp/fp/fn=`121/19/8`
- typescript:method: recall=`0.832370`, precision=`0.795580`, tp/fp/fn=`144/37/29`

## Call Resolution Diagnostics

- call_form.direct: tp=`1542`, fn=`19`, recall=`0.987828`
- call_form.member: tp=`158`, fn=`19`, recall=`0.892655`
- mismatch_attribution.core_missed_resolution: `0`
- mismatch_attribution.core_overresolution: `125`
- mismatch_attribution.normalization_contract_mismatch: `0`
- mismatch_attribution.independent_overprojection: `67`

## Out-of-Contract Distribution

- call: `237`

Breakdown by `edge_type::language::reason`:
- call::typescript::dynamic: `20`
- call::typescript::in_repo_unresolved: `150`
- call::typescript::standard_call: `67`

Note: `enrichment_edges` includes only in-repo out-of-contract edges (unresolved, dynamic, standard-call filtered); external edges are excluded.

## Independent Parser Coverage & Totals

- coverage.typescript: files_parsed/files_total=`348/348` (1.000000)
- raw_call_edges: `17353`
- raw_import_edges: `1973`
- normalized_call_edges: `17353`
- normalized_import_edges: `1973`
- contract_truth_edges: `1738`
- enrichment_edges: `200`
- enriched_truth_edges: `1938`

## Core Metrics

- static_contract_recall: `0.977560`
- static_overreach_rate: `0.052954`
- overreach_count: `95`
- reducer_edge_total: `1794`

## Metric Definitions & Schema

- report_schema_version: `2026-02-23`
- enriched_alignment_precision: layer=`enrichment_practical`, source=`reducer_vs_enriched_truth`, formula=`tp / (tp + fp)`
- enriched_alignment_recall: layer=`enrichment_practical`, source=`reducer_vs_enriched_truth`, formula=`tp / (tp + fn)`
- static_contract_precision: layer=`static_contract_alignment`, source=`reducer_vs_contract_truth`, formula=`tp / (tp + fp)`
- static_contract_recall: layer=`static_contract_alignment`, source=`reducer_vs_contract_truth`, formula=`tp / (tp + fn)`
- static_overreach_rate: layer=`static_contract_alignment`, source=`reducer_vs_contract_truth`, formula=`fp / (tp + fp)`
- static_projection_precision: layer=`internal_integrity`, source=`reducer_vs_db`, formula=`tp / (tp + fp)`
- static_projection_recall: layer=`internal_integrity`, source=`reducer_vs_db`, formula=`tp / (tp + fn)`

