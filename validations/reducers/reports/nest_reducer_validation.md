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
- scored_nodes: `316`
- avg_missing_rate/avg_spillover_rate: `0.085586`/`0.000111`
- avg_mutual_accuracy: `0.914307`
- reference/candidate/intersection: `1774`/`1725`/`1719`
- missing/spillover: `55`/`6`
- filtering_source: `core_only`
- envelope_reference/excluded/total: `1774`/`1035`/`2809`
- contract_filtered_out_ratio: `0.368459`
- class_truth_unreliable_count: `18`
- class_truth_unreliable_scored_excluded_count: `18`
- class_match_strategy_breakdown: `{'exact_qname': 107, 'none': 18}`
- match_provenance_breakdown: `{'qname_exact': 1719}`
- strict_contract_candidate_count_histogram: `{'0': 279, '1': 283, '11': 10, '12': 20, '17': 5, '18': 5, '19': 1, '2': 66, '20': 30, '28': 4, '3': 20, '35': 1, '4': 28, '48': 1, '5': 23, '6': 19, '7': 1, '79': 22, '8': 2, '9': 5}`
- core_contract_overlap: `{'reference_count': 1774, 'candidate_count': 1725, 'intersection_count': 1719, 'missing_count': 55, 'spillover_count': 6, 'avg_missing_rate': 0.08558619650391802, 'avg_spillover_rate': 0.0001110370863868532, 'avg_mutual_accuracy': 0.9143065303787252}`
- contract_plus_resolution_hints: `{'reference_count': 2117, 'candidate_count': 1725, 'intersection_count': 1719, 'missing_count': 398, 'spillover_count': 6, 'avg_missing_rate': 0.32291661993734533, 'avg_spillover_rate': 0.0033292427961094445, 'avg_mutual_accuracy': 0.6769955606194299}`
- by_language: `{'typescript': {'scored_nodes': 316, 'avg_missing_rate': 0.08558619650391802, 'avg_spillover_rate': 0.0001110370863868532, 'avg_mutual_accuracy': 0.9143065303787252, 'pass': False}}`

## Q2a. Reducers vs Independent Syntax Baseline

- scored_nodes: `500`
- reference/candidate/intersection: `1805`/`2734`/`1218`
- missing/spillover: `587`/`1516`
- coverage/spillover_ratio: `0.674792`/`0.839889`

## Q3. Beyond Static Contract Envelope

- scored_nodes: `316`
- avg_non_static_rate_percent: `0.95%`
- decorator_rate_percent: `0.00%`
- dynamic_dispatch_rate_percent: `0.95%`
- avg_non_static_percent_by_type: `{'dynamic_call': '0.95%'}`
- unresolved_static_target_zero: `True`
- unresolved_static_pass: `False`
- unresolved_static_avg_percent: `32.11%`

