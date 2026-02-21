# SCIONA Reducer Validation Report

## Executive Summary

- repo=nest
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

- contract_recall: `0.944216`
- overreach_rate: `0.084282`
- overreach_count: `148`
- reducer_edge_total: `1756`

## Determinism

- stability_score: `1.000000`
- stability_hashes: `['fdd4256ef4237908dc0d6b50ed2f241a33f1ae1d243196e1f5c3a21b116a9106', 'fdd4256ef4237908dc0d6b50ed2f241a33f1ae1d243196e1f5c3a21b116a9106']`

## Call Form Recall

- direct: tp=`1511`, fn=`60`, recall=`0.961808`
- member: tp=`99`, fn=`33`, recall=`0.750000`

## Independent Parser Totals

- raw_call_edges: `17460`
- raw_import_edges: `2000`
- normalized_call_edges: `17460`
- normalized_import_edges: `2000`
- contract_truth_edges: `1703`
- enrichment_edges: `251`

## Out-of-Contract Distribution

- call: `283`

Breakdown by `edge_type::language::reason`:
- call::typescript::dynamic: `19`
- call::typescript::in_repo_unresolved: `184`
- call::typescript::standard_call: `80`

Note: `enrichment_edges` includes only in-repo out-of-contract edges (unresolved, dynamic, standard-call filtered); external edges are excluded.
