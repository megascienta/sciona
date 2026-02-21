# SCIONA Reducer Validation Report

## Executive Summary

- repo=fastapi
- sampled_nodes=500
- invariants_passed=True
- full_recall=0.4062371768567911
- contract_recall=0.9580645161290322
- overreach_rate=0.0020161290322580645

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

- full_recall: `0.4062371768567911`
- contract_recall: `0.9580645161290322`
- overreach_rate: `0.0020161290322580645`
- overreach_count: `6`
- reducer_edge_total: `2976`

## Determinism

- stability_score: `1.0`
- stability_hashes: `['27939561d7d111c89bcc7795c1d00a016e7e8bd4e0261e5f5e8e841d8167224b', '27939561d7d111c89bcc7795c1d00a016e7e8bd4e0261e5f5e8e841d8167224b', '27939561d7d111c89bcc7795c1d00a016e7e8bd4e0261e5f5e8e841d8167224b']`

## Independent Parser Totals

- raw_call_edges: `15400`
- raw_import_edges: `4856`
- normalized_call_edges: `15400`
- normalized_import_edges: `4856`
- filtered_in_contract_edges: `3100`
- full_truth_edges: `7311`
- out_of_contract_edges: `4205`
