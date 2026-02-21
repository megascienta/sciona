# SCIONA Reducer Validation Report

## Executive Summary

- repo=nest
- sampled_nodes=500
- invariants_passed=True
- full_recall=0.40278422273781905
- contract_recall=0.8765027322404372
- overreach_rate=0.49913444893248704

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

- full_recall: `0.40278422273781905`
- contract_recall: `0.8765027322404372`
- overreach_rate: `0.49913444893248704`
- overreach_count: `865`
- reducer_edge_total: `1733`

## Determinism

- stability_score: `1.0`
- stability_hashes: `['3bfb24d066aaf7f0308231c48ec70bc98cb195c29464e19e601c749b3dc809d4', '3bfb24d066aaf7f0308231c48ec70bc98cb195c29464e19e601c749b3dc809d4', '3bfb24d066aaf7f0308231c48ec70bc98cb195c29464e19e601c749b3dc809d4']`

## Independent Parser Totals

- raw_call_edges: `18196`
- raw_import_edges: `2080`
- normalized_call_edges: `18196`
- normalized_import_edges: `2080`
- filtered_in_contract_edges: `915`
- full_truth_edges: `2155`
- out_of_contract_edges: `1239`
