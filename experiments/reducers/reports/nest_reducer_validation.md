# SCIONA Reducer Validation Report

## Executive Summary

- repo=nest
- sampled_nodes=500
- invariants_passed=False
- full_recall=0.5224568138195778
- contract_recall=0.9288762446657184
- overreach_rate=0.22494305239179954

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

- full_recall: `0.5224568138195778`
- contract_recall: `0.9288762446657184`
- overreach_rate: `0.22494305239179954`
- overreach_count: `395`
- reducer_edge_total: `1756`

## Determinism

- stability_score: `1.0`
- stability_hashes: `['6829dfb5ac03d93ccd22b409923ec6999875cbfbe896f16b30f78e223a2482ff', '6829dfb5ac03d93ccd22b409923ec6999875cbfbe896f16b30f78e223a2482ff']`

## Independent Parser Totals

- raw_call_edges: `17460`
- raw_import_edges: `2000`
- normalized_call_edges: `17460`
- normalized_import_edges: `2000`
- filtered_in_contract_edges: `1406`
- full_truth_edges: `2605`
- out_of_contract_edges: `1199`
