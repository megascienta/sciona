# SCIONA Reducer Validation Report

## Executive Summary

- repo=commons_lang
- sampled_nodes=500
- invariants_passed=True

## Hard Invariants

- passed: `True`
- gate_reducer_db_exact: `True`
- gate_aligned_scoring: `True`
- gate_parse_coverage: `True`
- gate_contract_truth_pure: `True`
- gate_contract_truth_resolved: `True`
- gate_parser_deterministic: `True`
- gate_no_duplicate_contract_edges: `True`
- gate_typescript_relative_index_contract: `True`
- gate_class_truth_nonempty_rate: `True`
- gate_scoped_call_normalization: `True`
- gate_equal_contract_metrics_when_exact: `True`

## Core Metrics

- contract_recall: `0.793698`
- overreach_rate: `0.016643`
- overreach_count: `81`
- reducer_edge_total: `4867`

## Determinism

- stability_score: `1.000000`
- stability_hashes: `['ac7e43f661bff845e0fec5925e4506bac56b165052bb4950e56d1d62d69d0932', 'ac7e43f661bff845e0fec5925e4506bac56b165052bb4950e56d1d62d69d0932']`

## Call Form Recall

- direct: tp=`4836`, fn=`1194`, recall=`0.801990`
- member: tp=`0`, fn=`0`, recall=`None`

## Independent Parser Totals

- raw_call_edges: `71438`
- raw_import_edges: `2518`
- normalized_call_edges: `71438`
- normalized_import_edges: `2518`
- contract_truth_edges: `6030`
- enrichment_edges: `124`

## Out-of-Contract Distribution

- call: `367`

Breakdown by `edge_type::language::reason`:
- call::java::in_repo_unresolved: `337`
- call::java::standard_call: `30`

Note: `enrichment_edges` includes only in-repo out-of-contract edges (unresolved, dynamic, standard-call filtered); external edges are excluded.
