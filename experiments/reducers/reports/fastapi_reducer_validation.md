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
- gate_class_truth_match_rate: `True`
- gate_scoped_call_normalization: `True`
- gate_contract_recall_min: `True`
- gate_overreach_rate_max: `True`
- gate_member_call_recall_min: `True`
- gate_equal_contract_metrics_when_exact: `True`

## Static Structural Validity

- valid: `True`
- static_contract_precision: `0.997686`
- static_contract_recall: `0.972294`
- static_overreach_rate: `0.002314`

## Semantic Alignment

- semantic_contract_precision: `0.997686`
- semantic_contract_recall: `0.972294`
- semantic_divergence_index: `0.029894`

## Prompt Fitness

- navigation_structural_reliability: `0.987300`
- reasoning_structural_reliability: `0.753715`
- coupling_stability_index: `0.997686`
- enrichment_noise_ratio: `0.043451`

## Core Metrics

- contract_recall: `0.972294`
- overreach_rate: `0.002314`
- overreach_count: `7`
- reducer_edge_total: `3025`

## Determinism

- stability_score: `1.000000`
- stability_hashes: `['9aebde700e17961f05bad669c7b5ea05e61076c9acd8ac7b5441389a1478df68', '9aebde700e17961f05bad669c7b5ea05e61076c9acd8ac7b5441389a1478df68']`

## Call Form Recall

- direct: tp=`2916`, fn=`64`, recall=`0.978523`
- member: tp=`106`, fn=`18`, recall=`0.854839`

## Language Breakdown

- python: sampled_nodes=`500`, population_nodes=`6363`, recall=`0.972294`, overreach_rate=`0.002314`, tp/fp/fn=`3018/7/86`
- python:module: recall=`0.989814`, precision=`0.997434`, tp/fp/fn=`2721/7/28`
- python:class: recall=`1.000000`, precision=`1.000000`, tp/fp/fn=`84/0/0`
- python:function: recall=`0.872340`, precision=`1.000000`, tp/fp/fn=`123/0/18`
- python:method: recall=`0.692308`, precision=`1.000000`, tp/fp/fn=`90/0/40`

## Independent Parser Totals

- raw_call_edges: `15400`
- raw_import_edges: `4856`
- normalized_call_edges: `15400`
- normalized_import_edges: `4856`
- contract_truth_edges: `3104`
- enrichment_edges: `141`

## Mismatch Attribution

- core_missed_resolution: `0`
- core_overresolution: `19`
- normalization_contract_mismatch: `0`
- independent_overprojection: `94`

## Out-of-Contract Distribution

- call: `197`
- import: `7`

Breakdown by `edge_type::language::reason`:
- call::python::dynamic: `13`
- call::python::in_repo_unresolved: `100`
- call::python::standard_call: `84`
- import::python::in_repo_unresolved: `1`
- import::python::relative_unresolved: `6`

Note: `enrichment_edges` includes only in-repo out-of-contract edges (unresolved, dynamic, standard-call filtered); external edges are excluded.
