# SCIONA Reducer Validation Report

## Q1. Reducers vs DB Correctness

- pass: `True`
- exact_required: `True`
- tp/fp/fn: `1777`/`0`/`0`
- mismatch_nodes: `0`

## Q2. Reducers vs Independent Within Static Contract

- pass: `False`
- target: `0.990000`
- precision/recall: `0.919612`/`0.992005`
- fp/fn: `141`/`13`
- contract_truth_edges: `1626`

## Q3. Beyond Static Contract Envelope

- descriptive_only: `True`
- total_edges: `396`
- uplift_vs_contract_truth: `0.243542`
- by_reason: `{'dynamic': 24, 'in_repo_unresolved': 372}`
- by_reason_percent: `{'dynamic': 0.06060606060606061, 'in_repo_unresolved': 0.9393939393939394}`
- by_edge_type: `{'call': 396}`

