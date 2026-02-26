# SCIONA Reducer Validation Report

## Q1. Reducers vs DB Correctness

- pass: `True`
- exact_required: `True`
- tp/fp/fn: `4909`/`0`/`0`
- mismatch_nodes: `0`

## Q2. Reducers vs Independent Within Static Contract

- pass: `False`
- target: `0.990000`
- precision/recall: `0.985333`/`0.993632`
- fp/fn: `72`/`31`
- contract_truth_edges: `4868`

## Q3. Beyond Static Contract Envelope

- descriptive_only: `True`
- total_edges: `3494`
- uplift_vs_contract_truth: `0.717749`
- by_reason: `{'in_repo_unresolved': 3494}`
- by_reason_percent: `{'in_repo_unresolved': 1.0}`
- by_edge_type: `{'call': 3494}`

