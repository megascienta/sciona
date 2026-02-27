# SCIONA Reducer Validation Report

## Q1. Reducers vs DB Correctness

- pass: `True`
- exact_required: `True`
- reference/candidate/intersection: `4909`/`4909`/`4909`
- missing/spillover: `0`/`0`
- mismatch_nodes: `0`

## Q2. Reducers vs Independent Within Static Contract

- pass: `False`
- target_mutual_accuracy_min: `0.990000`
- target_missing_rate_max: `0.010000`
- target_spillover_rate_max: `0.010000`
- scored_nodes: `366`
- avg_missing_rate/avg_spillover_rate: `0.117849`/`0.044275`
- avg_mutual_accuracy: `0.863765`
- reference/candidate/intersection: `4899`/`4871`/`4834`
- missing/spillover: `65`/`37`
- filtering_source: `core_only`
- by_language: `{'java': {'scored_nodes': 366, 'avg_missing_rate': 0.11784856764364961, 'avg_spillover_rate': 0.044275493660279025, 'avg_mutual_accuracy': 0.8637651507699742, 'pass': False}}`

## Q3. Beyond Static Contract Envelope

- scored_nodes: `366`
- avg_non_static_rate_percent: `0.00%`
- avg_non_static_percent_by_type: `{}`
- unresolved_static_target_zero: `True`
- unresolved_static_pass: `False`
- unresolved_static_avg_percent: `33.60%`

