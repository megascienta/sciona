# SCIONA Reducer Validation Report

## Executive Summary

- repo=fastapi
- sampled_nodes=500
- invariants_passed=False
- full_recall=0.4181633835457706
- contract_recall=0.9783124364622162
- overreach_rate=0.016689373297002725

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

- full_recall: `0.4181633835457706`
- contract_recall: `0.9783124364622162`
- overreach_rate: `0.016689373297002725`
- overreach_count: `49`
- reducer_edge_total: `2936`

## Determinism

- stability_score: `1.0`
- stability_hashes: `['49ae542622f8ae7d6985d3c55cea7aa8e878540f03dd4b728fd52c2dc02cfb85', '49ae542622f8ae7d6985d3c55cea7aa8e878540f03dd4b728fd52c2dc02cfb85']`

## Independent Parser Totals

- raw_call_edges: `15400`
- raw_import_edges: `4856`
- normalized_call_edges: `15400`
- normalized_import_edges: `4856`
- filtered_in_contract_edges: `2951`
- full_truth_edges: `6904`
- out_of_contract_edges: `3964`
