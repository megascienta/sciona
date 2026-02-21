# SCIONA Reducer Validation Report

## Executive Summary

- repo=fastapi
- sampled_nodes=500
- invariants_passed=True
- full_recall=0.4045657166013778
- contract_recall=0.9538216560509554
- overreach_rate=0.002664002664002664

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

- full_recall: `0.4045657166013778`
- contract_recall: `0.9538216560509554`
- overreach_rate: `0.002664002664002664`
- overreach_count: `8`
- reducer_edge_total: `3003`

## Determinism

- stability_score: `1.0`
- stability_hashes: `['0ee4a75ffe3851c97995f65a1c02ef023be12d3ef1e001530697a5ded150fa54', '0ee4a75ffe3851c97995f65a1c02ef023be12d3ef1e001530697a5ded150fa54']`

## Independent Parser Totals

- raw_call_edges: `15400`
- raw_import_edges: `4856`
- normalized_call_edges: `15400`
- normalized_import_edges: `4856`
- filtered_in_contract_edges: `3140`
- full_truth_edges: `7403`
- out_of_contract_edges: `4254`
