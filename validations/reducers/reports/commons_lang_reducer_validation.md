# SCIONA Reducer Validation Report

## Q1. Reducers vs DB Correctness

- pass: `True`
- exact_required: `True`
- tp/fp/fn: `4909`/`0`/`0`
- mismatch_nodes: `0`

## Q2. Reducers vs Independent Within Static Contract

- pass: `False`
- target: `0.990000`
- precision/recall: `0.986732`/`0.992404`
- fp/fn: `65`/`37`
- contract_truth_edges: `4871`
- filtering_source: `core_only`
- by_language: `{'java': {'tp': 4834, 'fp': 65, 'fn': 37, 'precision': 0.9867319861196162, 'recall': 0.9924040238144118, 'pass': False}}`

## Q3. Beyond Static Contract Envelope

- additional_vs_reducer_output_percent: `4.93%`
- percent_by_type: `{'direct_call_unresolved': '100.00%'}`

