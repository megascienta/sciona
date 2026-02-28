# SCIONA Reducer Validation Report

## Sampling

- seed: `20260219`
- requested_nodes: `500`
- sampled_nodes: `500`
- population_by_language: `{'java': 7162, 'python': 1960, 'typescript': 31}`
- population_by_kind: `{'class': 1559, 'function': 578, 'method': 5808, 'module': 1208}`
- sampled_by_language: `{'java': 208, 'python': 261, 'typescript': 31}`
- sampled_by_kind: `{'class': 129, 'function': 73, 'method': 148, 'module': 150}`

## Q1. Reducers vs DB Correctness

- pass: `True`
- exact_required: `True`
- reference/candidate/intersection: `1239`/`1239`/`1239`
- missing/spillover: `0`/`0`
- mismatch_nodes: `0`

## Q2. Reducers vs Independent Within Static Contract

- pass: `False`
- target_mutual_accuracy_min: `0.990000`
- target_missing_rate_max: `0.010000`
- target_spillover_rate_max: `0.010000`
- scored_nodes: `273`
- avg_missing_rate/avg_spillover_rate: `0.225600`/`0.009158`
- avg_mutual_accuracy: `0.770370`
- reference/candidate/intersection: `1197`/`1090`/`1083`
- missing/spillover: `114`/`7`
- filtering_source: `core_only`
- envelope_reference/excluded/total: `1197`/`4085`/`5282`
- contract_filtered_out_ratio: `0.773381`
- class_truth_unreliable_count: `2`
- class_truth_unreliable_scored_excluded_count: `2`
- class_match_strategy_breakdown: `{'exact_qname': 127, 'none': 2}`
- match_provenance_breakdown: `{'qname_exact': 1083}`
- strict_contract_candidate_count_histogram: `{'0': 1074, '1': 260, '10': 3, '102': 2, '12': 1, '121': 2, '13': 3, '14': 2, '2': 44, '27': 1, '28': 1, '29': 2, '3': 52, '32': 2, '33': 2, '35': 9, '36': 2, '4': 44, '40': 9, '5': 3, '54': 58, '6': 14, '7': 5, '8': 10}`
- core_contract_overlap: `{'reference_count': 1197, 'candidate_count': 1090, 'intersection_count': 1083, 'missing_count': 114, 'spillover_count': 7, 'avg_missing_rate': 0.2256003256003256, 'avg_spillover_rate': 0.009157509157509158, 'avg_mutual_accuracy': 0.7703703703703704}`
- contract_plus_resolution_hints: `{'reference_count': 1702, 'candidate_count': 1090, 'intersection_count': 1083, 'missing_count': 619, 'spillover_count': 7, 'avg_missing_rate': 0.44880742937304025, 'avg_spillover_rate': 0.0038461538461538464, 'avg_mutual_accuracy': 0.5500204094547986}`
- by_language: `{'java': {'scored_nodes': 133, 'avg_missing_rate': 0.12493734335839599, 'avg_spillover_rate': 0.0, 'avg_mutual_accuracy': 0.875062656641604, 'pass': False}, 'python': {'scored_nodes': 135, 'avg_missing_rate': 0.3331275720164609, 'avg_spillover_rate': 0.018518518518518517, 'avg_mutual_accuracy': 0.658724279835391, 'pass': False}, 'typescript': {'scored_nodes': 5, 'avg_missing_rate': 0.0, 'avg_spillover_rate': 0.0, 'avg_mutual_accuracy': 1.0, 'pass': True}}`

## Q2a. Reducers vs Independent Syntax Baseline

- scored_nodes: `500`
- reference/candidate/intersection: `1197`/`5174`/`1113`
- missing/spillover: `84`/`4061`
- coverage/spillover_ratio: `0.929825`/`3.392648`

## Q3. Beyond Static Contract Envelope

- scored_nodes: `273`
- avg_non_static_rate_percent: `0.37%`
- decorator_rate_percent: `0.00%`
- dynamic_dispatch_rate_percent: `0.37%`
- avg_non_static_percent_by_type: `{'dynamic_call': '0.37%'}`
- unresolved_static_target_zero: `True`
- unresolved_static_pass: `False`
- unresolved_static_avg_percent: `100.56%`

