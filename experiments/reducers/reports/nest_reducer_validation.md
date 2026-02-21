# SCIONA Reducer Validation Report

## Executive Summary

- repo=nest
- sampled_nodes=500
- invariants_passed=True
- full_recall=0.4994648590795576
- contract_recall=0.8965977318212142
- overreach_rate=0.19632606199770378

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
- gate_equal_full_metrics_when_exact: `True`

## Core Metrics

- full_recall: `0.4994648590795576`
- contract_recall: `0.8965977318212142`
- overreach_rate: `0.19632606199770378`
- overreach_count: `342`
- reducer_edge_total: `1742`

## Determinism

- stability_score: `1.0`
- stability_hashes: `['9dc411ba0526f2e6be72464f2d8b4029e3814f0f9c882a3aa43ca1af3b0d3ccd', '9dc411ba0526f2e6be72464f2d8b4029e3814f0f9c882a3aa43ca1af3b0d3ccd']`

## Independent Parser Totals

- raw_call_edges: `17414`
- raw_import_edges: `2041`
- normalized_call_edges: `17414`
- normalized_import_edges: `2041`
- filtered_in_contract_edges: `1499`
- full_truth_edges: `2803`
- out_of_contract_edges: `1303`
