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
- top_mismatch_signatures_count: `20`

## Q3. Beyond Static Contract Envelope

- additional_vs_reducer_output_percent: `22.99%`
- percent_by_type: `{'decorator_call': '13.57%', 'direct_call_unresolved': '58.14%', 'member_call_unresolved': '28.29%'}`
- additional_vs_reducer_output_percent_by_language: `{'java': '18.43%', 'python': '28.69%', 'typescript': '50.00%'}`
- percent_by_type_by_language: `{'java': {'direct_call_unresolved': 100.0}, 'python': {'decorator_call': 25.36231884057971, 'direct_call_unresolved': 23.18840579710145, 'member_call_unresolved': 51.449275362318836}, 'typescript': {'direct_call_unresolved': 33.33333333333333, 'member_call_unresolved': 66.66666666666666}}`

