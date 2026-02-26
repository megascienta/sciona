# SCIONA Reducer Validation Report

## Q1. Reducers vs DB Correctness

- pass: `True`
- exact_required: `True`
- tp/fp/fn: `1122`/`0`/`0`
- mismatch_nodes: `0`

## Q2. Reducers vs Independent Within Static Contract

- pass: `False`
- target: `0.990000`
- precision/recall: `0.939394`/`0.991533`
- fp/fn: `68`/`9`
- contract_truth_edges: `1063`

## Q3. Beyond Static Contract Envelope

- descriptive_only: `True`
- total_edges: `378`
- uplift_vs_contract_truth: `0.355597`
- by_reason: `{'in_repo_unresolved': 378}`
- by_reason_percent: `{'in_repo_unresolved': 1.0}`
- by_edge_type: `{'call': 378}`

