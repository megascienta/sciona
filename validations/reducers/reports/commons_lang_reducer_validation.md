# SCIONA Reducer Validation Report

## Sampling

- seed: `20260219`
- requested_nodes: `500`
- sampled_nodes: `500`
- population_by_language: `{'java': 9857}`
- population_by_kind: `{'class': 982, 'method': 8341, 'module': 534}`
- sampled_by_language: `{'java': 500}`
- sampled_by_kind: `{'class': 167, 'method': 167, 'module': 166}`

## Q1. Reducers vs DB Correctness

- pass: `True`
- exact_required: `True`
- reference/candidate/intersection: `4934`/`4934`/`4934`
- missing/spillover: `0`/`0`
- mismatch_nodes: `0`

## Q2. Reducers vs Independent Within Static Contract

- pass: `False`
- target_mutual_accuracy_min: `0.990000`
- target_missing_rate_max: `0.010000`
- target_spillover_rate_max: `0.010000`
- scored_nodes: `353`
- avg_missing_rate/avg_spillover_rate: `0.189400`/`0.000529`
- avg_mutual_accuracy: `0.810093`
- reference/candidate/intersection: `4905`/`4821`/`4815`
- missing/spillover: `90`/`6`
- filtering_source: `core_only`
- envelope_reference/excluded/total: `4905`/`2071`/`6976`
- contract_filtered_out_ratio: `0.296875`
- class_truth_unreliable_count: `1`
- class_truth_unreliable_scored_excluded_count: `1`
- class_match_strategy_breakdown: `{'exact_qname': 166, 'none': 1}`
- match_provenance_breakdown: `{'qname_exact': 4815}`
- strict_contract_candidate_count_histogram: `{'0': 342, '1': 169, '10': 4, '11': 4, '12': 1, '13': 1, '17': 4, '2': 27, '20': 5, '26': 1, '28': 6, '3': 19, '34': 1, '38': 6, '4': 11, '47': 8, '5': 11, '56': 3, '6': 9, '60': 1, '7': 13, '8': 3, '89': 9, '9': 2}`
- core_contract_overlap: `{'reference_count': 4905, 'candidate_count': 4821, 'intersection_count': 4815, 'missing_count': 90, 'spillover_count': 6, 'avg_missing_rate': 0.18940037771482532, 'avg_spillover_rate': 0.0005292991922690881, 'avg_mutual_accuracy': 0.8100925904573649}`
- contract_plus_resolution_hints: `{'reference_count': 5297, 'candidate_count': 4821, 'intersection_count': 4815, 'missing_count': 482, 'spillover_count': 6, 'avg_missing_rate': 0.37596382885904944, 'avg_spillover_rate': 0.000449140901132183, 'avg_mutual_accuracy': 0.6236059253832177}`
- by_language: `{'java': {'scored_nodes': 353, 'avg_missing_rate': 0.18940037771482532, 'avg_spillover_rate': 0.0005292991922690881, 'avg_mutual_accuracy': 0.8100925904573649, 'pass': False}}`

## Q2a. Reducers vs Independent Syntax Baseline

- scored_nodes: `500`
- reference/candidate/intersection: `4905`/`6838`/`4667`
- missing/spillover: `238`/`2171`
- coverage/spillover_ratio: `0.951478`/`0.442610`

## Q3. Beyond Static Contract Envelope

- scored_nodes: `353`
- avg_non_static_rate_percent: `0.00%`
- decorator_rate_percent: `0.00%`
- dynamic_dispatch_rate_percent: `0.00%`
- avg_non_static_percent_by_type: `{}`
- unresolved_static_target_zero: `True`
- unresolved_static_pass: `False`
- unresolved_static_avg_percent: `53.73%`

