# SCIONA Reducer Validation Report

## Executive Summary

- repo=fastapi
- sampled_nodes=500
- invariants_passed=False
- full_recall=0.4187241330098473
- contract_recall=0.9728116710875332
- overreach_rate=0.014112903225806451

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

- full_recall: `0.4187241330098473`
- contract_recall: `0.9728116710875332`
- overreach_rate: `0.014112903225806451`
- overreach_count: `42`
- reducer_edge_total: `2976`

## Determinism

- stability_score: `1.0`
- stability_hashes: `['bb0751bf445fe5f54f50a1bec947d238ccce734f3e07e1ff3e1f3b16cd0ea9c6', 'bb0751bf445fe5f54f50a1bec947d238ccce734f3e07e1ff3e1f3b16cd0ea9c6']`

## Independent Parser Totals

- raw_call_edges: `15400`
- raw_import_edges: `4856`
- normalized_call_edges: `15400`
- normalized_import_edges: `4856`
- filtered_in_contract_edges: `3016`
- full_truth_edges: `7007`
- out_of_contract_edges: `4001`
