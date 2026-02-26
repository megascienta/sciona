# SCIONA Reducer Validation Report

## Q1. Reducers vs DB Correctness

- pass: `True`
- exact_required: `True`
- tp/fp/fn: `1777`/`0`/`0`
- mismatch_nodes: `0`

## Q2. Reducers vs Independent Within Static Contract

- pass: `False`
- target: `0.990000`
- precision/recall: `0.978365`/`0.981314`
- fp/fn: `36`/`31`
- contract_truth_edges: `1659`
- filtering_source: `core_only`
- by_language: `{'typescript': {'tp': 1628, 'fp': 36, 'fn': 31, 'precision': 0.9783653846153846, 'recall': 0.9813140446051839, 'pass': False}}`

## Q3. Beyond Static Contract Envelope

- additional_vs_reducer_output_percent: `19.02%`
- percent_by_type: `{'decorator_call': '1.48%', 'direct_call_unresolved': '25.44%', 'dynamic_call': '5.03%', 'dynamic_member_call': '1.18%', 'member_call_unresolved': '66.86%'}`

