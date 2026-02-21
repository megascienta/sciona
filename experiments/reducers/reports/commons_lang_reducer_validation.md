# SCIONA Reducer Validation Report

## Executive Summary

- repo=commons_lang
- sampled_nodes=500
- invariants_passed=True
- full_recall=0.6479066575154427
- contract_recall=0.825725406935598
- overreach_rate=0.03159622486663931

## Hard Invariants

- passed: `True`
- gate_reducer_db_exact: `True`
- gate_aligned_scoring: `True`
- gate_parse_coverage: `True`
- gate_filter_subset: `True`
- gate_filter_resolved: `True`
- gate_parser_deterministic: `True`
- gate_no_duplicate_contract_edges: `True`
- gate_typescript_relative_index_contract: `True`
- gate_class_truth_nonempty_rate: `True`
- gate_scoped_call_normalization: `True`
- gate_equal_full_metrics_when_exact: `True`

## Core Metrics

- full_recall: `0.6479066575154427`
- contract_recall: `0.825725406935598`
- overreach_rate: `0.03159622486663931`
- overreach_count: `154`
- reducer_edge_total: `4874`

## Determinism

- stability_score: `1.0`
- stability_hashes: `['c4706fe3bf1708869fcdf43326e81bce78f1ce12e2b8b9454f313ffefa2c7606', 'c4706fe3bf1708869fcdf43326e81bce78f1ce12e2b8b9454f313ffefa2c7606']`

## Independent Parser Totals

- raw_call_edges: `71055`
- raw_import_edges: `2457`
- normalized_call_edges: `71055`
- normalized_import_edges: `2457`
- filtered_in_contract_edges: `5652`
- full_truth_edges: `7285`
- out_of_contract_edges: `1633`
