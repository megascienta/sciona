# SCIONA Reducer Validation Report

## Executive Summary

- repo=commons_lang
- sampled_nodes=500
- invariants_passed=True
- full_recall=0.6102772831340626
- contract_recall=0.7918284653047443
- overreach_rate=0.014177111156770084

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

- full_recall: `0.6102772831340626`
- contract_recall: `0.7918284653047443`
- overreach_rate: `0.014177111156770084`
- overreach_count: `69`
- reducer_edge_total: `4867`

## Determinism

- stability_score: `1.0`
- stability_hashes: `['ac7e43f661bff845e0fec5925e4506bac56b165052bb4950e56d1d62d69d0932', 'ac7e43f661bff845e0fec5925e4506bac56b165052bb4950e56d1d62d69d0932']`

## Independent Parser Totals

- raw_call_edges: `71438`
- raw_import_edges: `2518`
- normalized_call_edges: `71438`
- normalized_import_edges: `2518`
- filtered_in_contract_edges: `5923`
- full_truth_edges: `7862`
- out_of_contract_edges: `1939`
