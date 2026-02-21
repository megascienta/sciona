# SCIONA Reducer Validation Report

## Executive Summary

- repo=fastapi
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

- contract_recall: `0.978312`
- overreach_rate: `0.016689`
- overreach_count: `49`
- reducer_edge_total: `2936`

## Determinism

- stability_score: `1.000000`
- stability_hashes: `['49ae542622f8ae7d6985d3c55cea7aa8e878540f03dd4b728fd52c2dc02cfb85', '49ae542622f8ae7d6985d3c55cea7aa8e878540f03dd4b728fd52c2dc02cfb85']`

## Call Form Recall

- direct: tp=`2850`, fn=`44`, recall=`0.984796`
- member: tp=`37`, fn=`20`, recall=`0.649123`

## Independent Parser Totals

- raw_call_edges: `15400`
- raw_import_edges: `4856`
- normalized_call_edges: `15400`
- normalized_import_edges: `4856`
- contract_truth_edges: `2951`
- enrichment_edges: `84`

## Out-of-Contract Distribution

- call: `88`
- import: `4`

Breakdown by `edge_type::language::reason`:
- call::python::dynamic: `2`
- call::python::in_repo_unresolved: `59`
- call::python::standard_call: `27`
- import::python::in_repo_unresolved: `1`
- import::python::relative_unresolved: `3`

Note: `enrichment_edges` includes only in-repo out-of-contract edges (unresolved, dynamic, standard-call filtered); external edges are excluded.
