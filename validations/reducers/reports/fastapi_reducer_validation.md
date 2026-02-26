# SCIONA Reducer Validation Report

## Q1. Reducers vs DB Correctness

- pass: `True`
- exact_required: `True`
- tp/fp/fn: `2971`/`0`/`0`
- mismatch_nodes: `0`

## Q2. Reducers vs Independent Within Static Contract

- pass: `False`
- target: `0.990000`
- precision/recall: `0.979132`/`0.992494`
- fp/fn: `62`/`22`
- contract_truth_edges: `2931`

## Q3. Beyond Static Contract Envelope

- descriptive_only: `True`
- total_edges: `96`
- uplift_vs_contract_truth: `0.032753`
- by_reason: `{'dynamic': 7, 'in_repo_unresolved': 83, 'relative_unresolved': 6}`
- by_reason_percent: `{'dynamic': 0.07291666666666667, 'in_repo_unresolved': 0.8645833333333334, 'relative_unresolved': 0.0625}`
- by_edge_type: `{'call': 89, 'import': 7}`

