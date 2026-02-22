# SCIONA Reducer Validation Report

## Executive Summary

- repo=commons_lang
- sampled_nodes=500
- invariants_passed=True

## Hard Invariants

- passed: `True`
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

## Static Structural Validity

- valid: `True`
- static_contract_precision: `0.984521`
- static_contract_recall: `0.990371`
- static_overreach_rate: `0.015479`

## Semantic Alignment

- semantic_contract_precision: `0.984521`
- semantic_contract_recall: `0.990371`
- semantic_divergence_index: `0.024813`

## Prompt Fitness

- navigation_structural_reliability: `0.847458`
- reasoning_structural_reliability: `0.657051`
- coupling_stability_index: `0.984521`
- enrichment_noise_ratio: `0.022627`

## Core Metrics

- contract_recall: `0.990371`
- overreach_rate: `0.015479`
- overreach_count: `76`
- reducer_edge_total: `4913`

## Determinism

- stability_score: `1.000000`
- stability_hashes: `['6049416d671f5e01750d27a16b19612a85d3e4529b7447c62a024d7869a484c6', '6049416d671f5e01750d27a16b19612a85d3e4529b7447c62a024d7869a484c6']`

## Call Form Recall

- direct: tp=`4834`, fn=`47`, recall=`0.990371`
- member: tp=`0`, fn=`0`, recall=`None`

## Language Breakdown

- java: sampled_nodes=`500`, population_nodes=`9722`, recall=`0.990371`, overreach_rate=`0.015479`, tp/fp/fn=`4834/76/47`
- java:module: recall=`1.000000`, precision=`0.847458`, tp/fp/fn=`200/36/0`
- java:class: recall=`0.997991`, precision=`1.000000`, tp/fp/fn=`4470/0/9`
- java:method: recall=`0.811881`, precision=`0.803922`, tp/fp/fn=`164/40/38`

## Independent Parser Totals

- raw_call_edges: `70293`
- raw_import_edges: `2537`
- normalized_call_edges: `70293`
- normalized_import_edges: `2537`
- contract_truth_edges: `4881`
- enrichment_edges: `113`

## Mismatch Attribution

- core_missed_resolution: `0`
- core_overresolution: `1242`
- normalization_contract_mismatch: `0`
- independent_overprojection: `1210`

## Out-of-Contract Distribution

- call: `292`

Breakdown by `edge_type::language::reason`:
- call::java::in_repo_unresolved: `260`
- call::java::standard_call: `32`

Note: `enrichment_edges` includes only in-repo out-of-contract edges (unresolved, dynamic, standard-call filtered); external edges are excluded.
