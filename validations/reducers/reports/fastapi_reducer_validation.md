# SCIONA Reducer Validation Report

## Q1. Reducers vs DB Correctness

- pass: `True`
- exact_required: `True`
- tp/fp/fn: `2971`/`0`/`0`
- mismatch_nodes: `0`

## Q2. Reducers vs Independent Within Static Contract

- pass: `False`
- target: `0.990000`
- precision/recall: `0.979791`/`0.992494`
- fp/fn: `60`/`22`
- contract_truth_edges: `2931`
- filtering_source: `core_only`
- by_language: `{'python': {'tp': 2909, 'fp': 60, 'fn': 22, 'precision': 0.9797911754799595, 'recall': 0.9924940293415216, 'pass': False}}`
- top_mismatch_signatures_count: `20`

## Q3. Beyond Static Contract Envelope

- additional_vs_reducer_output_percent: `3.06%`
- percent_by_type: `{'decorator_call': '42.86%', 'direct_call_unresolved': '4.40%', 'dynamic_call': '4.40%', 'member_call_unresolved': '42.86%', 'module_import_unresolved': '1.10%', 'relative_import_unresolved': '4.40%'}`
- additional_vs_reducer_output_percent_by_language: `{'python': '3.06%'}`
- percent_by_type_by_language: `{'python': {'decorator_call': 42.857142857142854, 'direct_call_unresolved': 4.395604395604396, 'dynamic_call': 4.395604395604396, 'member_call_unresolved': 42.857142857142854, 'module_import_unresolved': 1.098901098901099, 'relative_import_unresolved': 4.395604395604396}}`

