# SCIONA Reducer Validation Report

## Executive Summary

- repo=sciona
- sampled_nodes=30
- invariants_passed=False
- contract_recall=0.625
- overreach_rate=0.4117647058823529

## Hard Invariants

- passed: `False`
- gate_reducer_db_exact: `True`
- gate_aligned_scoring: `True`
- gate_parse_coverage: `True`
- gate_contract_truth_pure: `True`
- gate_contract_truth_resolved: `True`
- gate_parser_deterministic: `True`
- gate_no_duplicate_contract_edges: `True`
- gate_typescript_relative_index_contract: `True`
- gate_class_truth_nonempty_rate: `False`
- gate_scoped_call_normalization: `True`
- gate_equal_contract_metrics_when_exact: `True`
- failure: class truth quality gate failed: too many class nodes have empty full truth with parse_ok

## Core Metrics

- contract_recall: `0.625`
- overreach_rate: `0.4117647058823529`
- overreach_count: `21`
- reducer_edge_total: `51`

## Determinism

- stability_score: `1.0`
- stability_hashes: `['bd2a846590bc05e49a4b4763c9555276f24da780ee37b7ad29455822ea82a6d3', 'bd2a846590bc05e49a4b4763c9555276f24da780ee37b7ad29455822ea82a6d3']`

## Independent Parser Totals

- raw_call_edges: `1738`
- raw_import_edges: `211`
- normalized_call_edges: `1738`
- normalized_import_edges: `211`
- contract_truth_edges: `48`
- enrichment_edges: `128`
