# SCIONA Reducer Validation Report

## Q1. Reducers vs DB Correctness

- pass: `True`
- exact_required: `True`
- tp/fp/fn: `265`/`0`/`0`
- mismatch_nodes: `0`

## Q2. Reducers vs Independent Within Static Contract

- pass: `False`
- target: `0.990000`
- precision/recall: `0.893701`/`0.957806`
- fp/fn: `27`/`10`
- contract_truth_edges: `237`
- filtering_source: `core_only`
- by_language: `{'java': {'tp': 26, 'fp': 0, 'fn': 0, 'precision': 1.0, 'recall': 1.0, 'pass': True}, 'python': {'tp': 187, 'fp': 12, 'fn': 10, 'precision': 0.9396984924623115, 'recall': 0.949238578680203, 'pass': False}, 'typescript': {'tp': 14, 'fp': 15, 'fn': 0, 'precision': 0.4827586206896552, 'recall': 1.0, 'pass': False}}`

## Q3. Beyond Static Contract Envelope

- additional_vs_reducer_output_percent: `137.36%`
- percent_by_type: `{'decorator_call': '1.37%', 'direct_call_unresolved': '5.22%', 'dynamic_call': '1.10%', 'member_call_unresolved': '5.22%', 'module_import_unresolved': '84.34%', 'relative_import_unresolved': '2.75%'}`

