# SCIONA Reducer Validation Report

## Sampling

- seed: `20260219`
- requested_nodes: `500`
- sampled_nodes: `500`
- population_by_language: `{'python': 6356}`
- population_by_kind: `{'class': 658, 'function': 4178, 'method': 236, 'module': 1284}`
- sampled_by_language: `{'python': 500}`
- sampled_by_kind: `{'class': 125, 'function': 125, 'method': 125, 'module': 125}`

## Q1. Reducers vs DB Correctness

- pass: `True`
- exact_required: `True`
- reference/candidate/intersection: `2998`/`2998`/`2998`
- missing/spillover: `0`/`0`
- mismatch_nodes: `0`

## Q2. Reducers vs Independent Within Static Contract

- pass: `False`
- target_mutual_accuracy_min: `0.990000`
- target_missing_rate_max: `0.010000`
- target_spillover_rate_max: `0.010000`
- scored_nodes: `248`
- avg_missing_rate/avg_spillover_rate: `0.181250`/`0.011250`
- avg_mutual_accuracy: `0.811481`
- reference/candidate/intersection: `2998`/`2958`/`2934`
- missing/spillover: `64`/`24`
- filtering_source: `core_only`
- envelope_reference/excluded/total: `2998`/`4272`/`7270`
- contract_filtered_out_ratio: `0.587620`
- class_truth_unreliable_count: `0`
- class_truth_unreliable_scored_excluded_count: `0`
- class_match_strategy_breakdown: `{'exact_qname': 125}`
- match_provenance_breakdown: `{'qname_exact': 2934}`
- strict_contract_candidate_count_histogram: `{'0': 376, '1': 146, '138': 2, '2': 53, '3': 30, '4': 4, '40': 1, '6': 8, '68': 12, '9': 49}`
- core_contract_overlap: `{'reference_count': 2998, 'candidate_count': 2958, 'intersection_count': 2934, 'missing_count': 64, 'spillover_count': 24, 'avg_missing_rate': 0.18125, 'avg_spillover_rate': 0.011250120747555216, 'avg_mutual_accuracy': 0.8114810088177135}`
- contract_plus_resolution_hints: `{'reference_count': 3192, 'candidate_count': 2958, 'intersection_count': 2934, 'missing_count': 258, 'spillover_count': 24, 'avg_missing_rate': 0.3855352959797404, 'avg_spillover_rate': 0.005586092919426252, 'avg_mutual_accuracy': 0.6109042464434621}`
- by_language: `{'python': {'scored_nodes': 248, 'avg_missing_rate': 0.18125, 'avg_spillover_rate': 0.011250120747555216, 'avg_mutual_accuracy': 0.8114810088177135, 'pass': False}}`

## Q2a. Reducers vs Independent Syntax Baseline

- scored_nodes: `500`
- reference/candidate/intersection: `2998`/`7199`/`2704`
- missing/spillover: `294`/`4495`
- coverage/spillover_ratio: `0.901935`/`1.499333`

## Q3. Beyond Static Contract Envelope

- scored_nodes: `248`
- avg_non_static_rate_percent: `1.69%`
- decorator_rate_percent: `0.00%`
- dynamic_dispatch_rate_percent: `1.69%`
- avg_non_static_percent_by_type: `{'dynamic_call': '1.29%', 'dynamic_member_call': '0.40%'}`
- unresolved_static_target_zero: `True`
- unresolved_static_pass: `False`
- unresolved_static_avg_percent: `37.29%`

