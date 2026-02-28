# SCIONA Reducer Validation Report

## Sampling

- seed: `20260219`
- requested_nodes: `500`
- sampled_nodes: `500`
- population_by_language: `{'typescript': 6724}`
- population_by_kind: `{'class': 1669, 'function': 289, 'method': 3107, 'module': 1659}`
- sampled_by_language: `{'typescript': 500}`
- sampled_by_kind: `{'class': 125, 'function': 125, 'method': 125, 'module': 125}`

## Q1. Reducers vs DB Correctness

- pass: `True`
- exact_required: `True`
- reference/candidate/intersection: `1826`/`1826`/`1826`
- missing/spillover: `0`/`0`
- mismatch_nodes: `0`

## Q2. Reducers vs Independent Within Static Contract

- pass: `False`
- target_mutual_accuracy_min: `0.990000`
- target_missing_rate_max: `0.010000`
- target_spillover_rate_max: `0.010000`
- scored_nodes: `323`
- avg_missing_rate/avg_spillover_rate: `0.119335`/`0.004753`
- avg_mutual_accuracy: `0.877980`
- reference/candidate/intersection: `1775`/`1715`/`1709`
- missing/spillover: `66`/`6`
- filtering_source: `core_only`
- envelope_reference/excluded/total: `1775`/`1028`/`2803`
- contract_filtered_out_ratio: `0.366750`
- class_truth_unreliable_count: `18`
- class_truth_unreliable_scored_excluded_count: `18`
- class_match_strategy_breakdown: `{'exact_qname': 107, 'none': 18}`
- match_provenance_breakdown: `{'qname_exact': 1709}`
- strict_contract_candidate_count_histogram: `{'0': 401, '1': 294, '11': 1, '13': 3, '17': 1, '18': 9, '19': 4, '2': 46, '20': 1, '3': 20, '4': 10, '5': 11, '6': 8, '7': 11, '8': 2, '9': 3}`
- core_contract_overlap: `{'reference_count': 1775, 'candidate_count': 1715, 'intersection_count': 1709, 'missing_count': 66, 'spillover_count': 6, 'avg_missing_rate': 0.11933510246203745, 'avg_spillover_rate': 0.004752593558198903, 'avg_mutual_accuracy': 0.8779799698648416}`
- contract_plus_resolution_hints: `{'reference_count': 2080, 'candidate_count': 1715, 'intersection_count': 1709, 'missing_count': 371, 'spillover_count': 6, 'avg_missing_rate': 0.3104208625599, 'avg_spillover_rate': 0.0023219814241486067, 'avg_mutual_accuracy': 0.688597234663581}`
- by_language: `{'typescript': {'scored_nodes': 323, 'avg_missing_rate': 0.11933510246203745, 'avg_spillover_rate': 0.004752593558198903, 'avg_mutual_accuracy': 0.8779799698648416, 'pass': False}}`

## Q2a. Reducers vs Independent Syntax Baseline

- scored_nodes: `500`
- reference/candidate/intersection: `1806`/`2734`/`1219`
- missing/spillover: `587`/`1515`
- coverage/spillover_ratio: `0.674972`/`0.838870`

## Q3. Beyond Static Contract Envelope

- scored_nodes: `323`
- avg_non_static_rate_percent: `0.93%`
- decorator_rate_percent: `0.00%`
- dynamic_dispatch_rate_percent: `0.93%`
- avg_non_static_percent_by_type: `{'dynamic_call': '0.93%'}`
- unresolved_static_target_zero: `True`
- unresolved_static_pass: `False`
- unresolved_static_avg_percent: `34.22%`

