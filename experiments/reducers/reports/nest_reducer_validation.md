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
- gate_class_truth_match_rate: `True`
- gate_scoped_call_normalization: `True`
- gate_contract_recall_min: `True`
- gate_overreach_rate_max: `True`
- gate_member_call_recall_min: `True`
- gate_equal_contract_metrics_when_exact: `True`

## Static Structural Validity

- valid: `True`
- static_contract_precision: `0.947046`
- static_contract_recall: `0.977560`
- static_overreach_rate: `0.052954`

## Semantic Alignment

- semantic_contract_precision: `0.947046`
- semantic_contract_recall: `0.977560`
- semantic_divergence_index: `0.073104`

## Prompt Fitness

- navigation_structural_reliability: `0.998008`
- reasoning_structural_reliability: `0.725233`
- coupling_stability_index: `0.947046`
- enrichment_noise_ratio: `0.103199`

## Core Metrics

- contract_recall: `0.977560`
- overreach_rate: `0.052954`
- overreach_count: `95`
- reducer_edge_total: `1794`

## Determinism

- stability_score: `1.000000`
- stability_hashes: `['84406c4ab00265f54718b192a51a7f2b566f700d2421e757f2abfebe6a4beaa4', '84406c4ab00265f54718b192a51a7f2b566f700d2421e757f2abfebe6a4beaa4']`

## Call Form Recall

- direct: tp=`1542`, fn=`19`, recall=`0.987828`
- member: tp=`158`, fn=`19`, recall=`0.892655`

## Language Breakdown

- typescript: sampled_nodes=`500`, population_nodes=`6033`, recall=`0.977560`, overreach_rate=`0.052954`, tp/fp/fn=`1699/95/39`
- typescript:module: recall=`1.000000`, precision=`0.998008`, tp/fp/fn=`501/1/0`
- typescript:class: recall=`0.997861`, precision=`0.960865`, tp/fp/fn=`933/38/2`
- typescript:function: recall=`0.937984`, precision=`0.864286`, tp/fp/fn=`121/19/8`
- typescript:method: recall=`0.832370`, precision=`0.795580`, tp/fp/fn=`144/37/29`

## Independent Parser Totals

- raw_call_edges: `17353`
- raw_import_edges: `1973`
- normalized_call_edges: `17353`
- normalized_import_edges: `1973`
- contract_truth_edges: `1738`
- enrichment_edges: `200`

## Mismatch Attribution

- core_missed_resolution: `0`
- core_overresolution: `125`
- normalization_contract_mismatch: `0`
- independent_overprojection: `67`

## Out-of-Contract Distribution

- call: `237`

Breakdown by `edge_type::language::reason`:
- call::typescript::dynamic: `20`
- call::typescript::in_repo_unresolved: `150`
- call::typescript::standard_call: `67`

Note: `enrichment_edges` includes only in-repo out-of-contract edges (unresolved, dynamic, standard-call filtered); external edges are excluded.
