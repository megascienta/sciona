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
- avg_missing_rate/avg_spillover_rate: `0.245849`/`0.005495`
- avg_mutual_accuracy: `0.751099`
- reference/candidate/intersection: `1197`/`1077`/`1074`
- missing/spillover: `123`/`3`
- filtering_source: `core_only`
- envelope_reference/excluded/total: `1197`/`4319`/`5516`
- contract_filtered_out_ratio: `0.782995`
- class_truth_unreliable_count: `2`
- class_truth_unreliable_scored_excluded_count: `2`
- class_match_strategy_breakdown: `{'exact_qname': 127, 'none': 2}`
- match_provenance_breakdown: `{'qname_exact': 1074}`
- strict_contract_candidate_count_histogram: `{'0': 1143, '1': 291, '10': 1, '102': 2, '12': 7, '121': 5, '127': 1, '13': 3, '14': 1, '18': 1, '2': 42, '28': 1, '29': 2, '3': 32, '33': 2, '35': 2, '36': 8, '4': 18, '40': 9, '5': 3, '54': 9, '6': 12, '7': 6, '8': 4}`
- core_contract_overlap: `{'reference_count': 1197, 'candidate_count': 1077, 'intersection_count': 1074, 'missing_count': 123, 'spillover_count': 3, 'avg_missing_rate': 0.24584859584859584, 'avg_spillover_rate': 0.005494505494505495, 'avg_mutual_accuracy': 0.7510989010989011}`
- contract_plus_resolution_hints: `{'reference_count': 1840, 'candidate_count': 1077, 'intersection_count': 1074, 'missing_count': 766, 'spillover_count': 3, 'avg_missing_rate': 0.4682656841413032, 'avg_spillover_rate': 0.001834862385321101, 'avg_mutual_accuracy': 0.5311809446631237}`
- by_language: `{'java': {'scored_nodes': 133, 'avg_missing_rate': 0.1324561403508772, 'avg_spillover_rate': 0.0, 'avg_mutual_accuracy': 0.8675438596491228, 'pass': False}, 'python': {'scored_nodes': 135, 'avg_missing_rate': 0.36666666666666664, 'avg_spillover_rate': 0.011111111111111112, 'avg_mutual_accuracy': 0.6271604938271605, 'pass': False}, 'typescript': {'scored_nodes': 5, 'avg_missing_rate': 0.0, 'avg_spillover_rate': 0.0, 'avg_mutual_accuracy': 1.0, 'pass': True}}`

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
- unresolved_static_avg_percent: `140.13%`

