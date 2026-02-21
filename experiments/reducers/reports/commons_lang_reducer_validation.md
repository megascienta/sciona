# SCIONA Reducer Validation Report

## Executive Summary

- repo=commons_lang
- sampled_nodes=500
- invariants_passed=True
- full_recall=0.705213133640553
- contract_recall=0.9457379636937648
- overreach_rate=0.01448983698933387

## Hard Invariants

- passed: `True`
- gate_reducer_db_exact: `True`
- gate_aligned_scoring: `True`
- gate_parse_coverage: `True`
- gate_filter_subset: `True`
- gate_filter_resolved: `True`
- gate_parser_deterministic: `True`
- gate_no_duplicate_contract_edges: `True`
- gate_equal_full_metrics_when_exact: `True`

## Core Metrics

- full_recall: `0.705213133640553`
- contract_recall: `0.9457379636937648`
- overreach_rate: `0.01448983698933387`
- overreach_count: `72`
- reducer_edge_total: `4969`

## Determinism

- stability_score: `1.0`
- stability_hashes: `['c81c4e55adca372ab253fa4e24ee0c0670e27fa4f1a4a92b10292f2bde3731b2', 'c81c4e55adca372ab253fa4e24ee0c0670e27fa4f1a4a92b10292f2bde3731b2', 'c81c4e55adca372ab253fa4e24ee0c0670e27fa4f1a4a92b10292f2bde3731b2']`

## Independent Parser Totals

- raw_call_edges: `69984`
- raw_import_edges: `2454`
- normalized_call_edges: `69984`
- normalized_import_edges: `2454`
- filtered_in_contract_edges: `5068`
- full_truth_edges: `6944`
- out_of_contract_edges: `1866`
