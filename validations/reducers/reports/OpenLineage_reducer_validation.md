# SCIONA Reducer Validation Report

## Q1. Reducers vs DB Correctness

- pass: `True`
- exact_required: `True`
- tp/fp/fn: `1122`/`0`/`0`
- mismatch_nodes: `0`

## Q2. Reducers vs Independent Within Static Contract

- pass: `False`
- target: `0.990000`
- precision/recall: `0.961609`/`0.987793`
- fp/fn: `42`/`13`
- contract_truth_edges: `1065`
- filtering_source: `core_only`
- by_language: `{'java': {'tp': 573, 'fp': 34, 'fn': 6, 'precision': 0.943986820428336, 'recall': 0.9896373056994818, 'pass': False}, 'python': {'tp': 473, 'fp': 8, 'fn': 7, 'precision': 0.9833679833679834, 'recall': 0.9854166666666667, 'pass': False}, 'typescript': {'tp': 6, 'fp': 0, 'fn': 0, 'precision': 1.0, 'recall': 1.0, 'pass': True}}`

## Q3. Beyond Static Contract Envelope

- additional_vs_reducer_output_percent: `23.17%`
- percent_by_type: `{'decorator_call': '13.46%', 'direct_call_unresolved': '58.46%', 'member_call_unresolved': '28.08%'}`

