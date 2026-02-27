# SCIONA Reducer Validation Report

## Q1. Reducers vs DB Correctness

- pass: `True`
- exact_required: `True`
- reference/candidate/intersection: `1777`/`1777`/`1777`
- missing/spillover: `0`/`0`
- mismatch_nodes: `0`

## Q2. Reducers vs Independent Within Static Contract

- pass: `False`
- target_mutual_accuracy_min: `0.990000`
- target_missing_rate_max: `0.010000`
- target_spillover_rate_max: `0.010000`
- scored_nodes: `272`
- avg_missing_rate/avg_spillover_rate: `0.076892`/`0.031853`
- avg_mutual_accuracy: `0.913138`
- reference/candidate/intersection: `1664`/`1659`/`1628`
- missing/spillover: `36`/`31`
- filtering_source: `core_only`
- by_language: `{'typescript': {'scored_nodes': 272, 'avg_missing_rate': 0.0768922152194211, 'avg_spillover_rate': 0.0318531469605386, 'avg_mutual_accuracy': 0.9131383874171137, 'pass': False}}`

## Q3. Beyond Static Contract Envelope

- scored_nodes: `272`
- avg_non_static_rate_percent: `2.57%`
- avg_non_static_percent_by_type: `{'decorator_call': '0.00%', 'dynamic_call': '2.57%', 'dynamic_member_call': '0.00%'}`
- unresolved_static_target_zero: `True`
- unresolved_static_pass: `False`
- unresolved_static_avg_percent: `25.28%`

