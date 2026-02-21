# SCIONA Reducer Validation Report

## Executive Summary

- repo=nest
- sampled_nodes=500
- invariants_passed=False
- full_recall=0.5037993920972644
- contract_recall=0.9117647058823529
- overreach_rate=0.23661485319516407

## Hard Invariants

- passed: `False`
- gate_reducer_db_exact: `True`
- gate_aligned_scoring: `True`
- gate_parse_coverage: `True`
- gate_filter_subset: `True`
- gate_filter_resolved: `True`
- gate_parser_deterministic: `True`
- gate_no_duplicate_contract_edges: `True`
- gate_typescript_relative_index_contract: `True`
- gate_class_truth_nonempty_rate: `False`
- gate_scoped_call_normalization: `True`
- gate_equal_full_metrics_when_exact: `True`
- failure: class truth quality gate failed: too many class nodes have empty full truth with parse_ok

## Core Metrics

- full_recall: `0.5037993920972644`
- contract_recall: `0.9117647058823529`
- overreach_rate: `0.23661485319516407`
- overreach_count: `411`
- reducer_edge_total: `1737`

## Determinism

- stability_score: `1.0`
- stability_hashes: `['679882911377804f43d296efd78dc450642d78bab0c504624ef0aa7fee6d8cca', '679882911377804f43d296efd78dc450642d78bab0c504624ef0aa7fee6d8cca']`

## Independent Parser Totals

- raw_call_edges: `17055`
- raw_import_edges: `2022`
- normalized_call_edges: `17055`
- normalized_import_edges: `2022`
- filtered_in_contract_edges: `1394`
- full_truth_edges: `2632`
- out_of_contract_edges: `1238`
