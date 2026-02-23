# SCIONA Reducer Validation Report

## Executive Summary

- repo=fastapi
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

- static_contract_precision: `0.997686`
- static_contract_recall: `0.972294`
- static_overreach_rate: `0.002314`
- static_divergence_index: `0.029894`

## Expanded Truth Alignment (Diagnostic)

- reducer_vs_enriched_truth_precision: `0.997686`
- reducer_vs_enriched_truth_recall: `0.930046`
- db_vs_enriched_truth_precision: `0.997686`
- db_vs_enriched_truth_recall: `0.930046`
- reducer_vs_enriched_truth_divergence_index: `0.071956`
- inclusion_policy: `{'base': 'contract_truth_edges + enrichment_edges', 'include_enrichment_reasons': ['dynamic', 'in_repo_unresolved', 'relative_unresolved', 'standard_call'], 'exclude_enrichment_reasons': ['external'], 'notes': 'Enriched truth is diagnostic-only and non-gating.'}`

## Prompt Reliability (Heuristic Diagnostics)

- navigation_structural_reliability: `0.987300`
- reasoning_structural_reliability: `0.753715`
- coupling_stability_index: `0.997686`
- weights: `{'navigation': {'fp_weight': 1.0, 'fn_weight': 1.0}, 'reasoning': {'fp_weight': 1.0, 'fn_weight': 1.2}}`
- enrichment_noise_ratio: `0.043451`

## Language Breakdown

- python: sampled_nodes=`500`, population_nodes=`6363`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`0.997686`/`0.972294`, expanded_p/r=`0.997686`/`0.930046`, contract_overreach=`0.002314`, projection_tp/fp/fn=`3025/0/0`, contract_tp/fp/fn=`3018/7/86`
- python:module: recall=`0.989814`, precision=`0.997434`, tp/fp/fn=`2721/7/28`
- python:class: recall=`1.000000`, precision=`1.000000`, tp/fp/fn=`84/0/0`
- python:function: recall=`0.872340`, precision=`1.000000`, tp/fp/fn=`123/0/18`
- python:method: recall=`0.692308`, precision=`1.000000`, tp/fp/fn=`90/0/40`

## Call Resolution Diagnostics

- call_form.direct: tp=`2916`, fn=`64`, recall=`0.978523`
- call_form.member: tp=`106`, fn=`18`, recall=`0.854839`
- mismatch_attribution.core_missed_resolution: `0`
- mismatch_attribution.core_overresolution: `19`
- mismatch_attribution.normalization_contract_mismatch: `0`
- mismatch_attribution.independent_overprojection: `94`

## Out-of-Contract Distribution

- call: `197`
- import: `7`

Breakdown by `edge_type::language::reason`:
- call::python::dynamic: `13`
- call::python::in_repo_unresolved: `100`
- call::python::standard_call: `84`
- import::python::in_repo_unresolved: `1`
- import::python::relative_unresolved: `6`

Note: `enrichment_edges` includes only in-repo out-of-contract edges (unresolved, dynamic, standard-call filtered); external edges are excluded.

## Independent Parser Coverage & Totals

- coverage.python: files_parsed/files_total=`1284/1284` (1.000000)
- raw_call_edges: `15400`
- raw_import_edges: `4856`
- normalized_call_edges: `15400`
- normalized_import_edges: `4856`
- contract_truth_edges: `3104`
- enrichment_edges: `141`
- enriched_truth_edges: `3245`

## Core Metrics

- static_contract_recall: `0.972294`
- static_overreach_rate: `0.002314`
- overreach_count: `7`
- reducer_edge_total: `3025`

## Metric Definitions & Schema

- report_schema_version: `2026-02-23`
- enriched_alignment_precision: layer=`enrichment_practical`, source=`reducer_vs_enriched_truth`, formula=`tp / (tp + fp)`
- enriched_alignment_recall: layer=`enrichment_practical`, source=`reducer_vs_enriched_truth`, formula=`tp / (tp + fn)`
- static_contract_precision: layer=`static_contract_alignment`, source=`reducer_vs_contract_truth`, formula=`tp / (tp + fp)`
- static_contract_recall: layer=`static_contract_alignment`, source=`reducer_vs_contract_truth`, formula=`tp / (tp + fn)`
- static_overreach_rate: layer=`static_contract_alignment`, source=`reducer_vs_contract_truth`, formula=`fp / (tp + fp)`
- static_projection_precision: layer=`internal_integrity`, source=`reducer_vs_db`, formula=`tp / (tp + fp)`
- static_projection_recall: layer=`internal_integrity`, source=`reducer_vs_db`, formula=`tp / (tp + fn)`

