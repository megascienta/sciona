# SCIONA Reducer Validation Report

## Executive Summary

- repo=commons_lang
- sampled_nodes=500
- invariants_passed=True
- full_recall=0.6933389782670054
- contract_recall=0.944804557061481
- overreach_rate=0.009675468655513001

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

- full_recall: `0.6933389782670054`
- contract_recall: `0.944804557061481`
- overreach_rate: `0.009675468655513001`
- overreach_count: `48`
- reducer_edge_total: `4961`

## Determinism

- stability_score: `1.0`
- stability_hashes: `['c1813df5a25dfe8ce1193f16115d4b39cef429ea16deb3cf1f5de55e5a3359a4', 'c1813df5a25dfe8ce1193f16115d4b39cef429ea16deb3cf1f5de55e5a3359a4']`

## Independent Parser Totals

- raw_call_edges: `69264`
- raw_import_edges: `2462`
- normalized_call_edges: `69264`
- normalized_import_edges: `2462`
- filtered_in_contract_edges: `5091`
- full_truth_edges: `7086`
- out_of_contract_edges: `1971`
