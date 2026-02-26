# SCIONA Reducer Validation Report

## Q1. Reducers vs DB Correctness

- pass: `True`
- exact_required: `True`
- tp/fp/fn: `1777`/`0`/`0`
- mismatch_nodes: `0`

## Q2. Reducers vs Independent Within Static Contract

- pass: `False`
- target: `0.990000`
- precision/recall: `0.958534`/`0.980935`
- fp/fn: `69`/`31`
- contract_truth_edges: `1626`
- filtering_source: `core_only`
- by_language: `{'typescript': {'tp': 1595, 'fp': 69, 'fn': 31, 'precision': 0.9585336538461539, 'recall': 0.9809348093480935, 'pass': False}}`
- top_mismatch_signatures_count: `20`

## Q3. Beyond Static Contract Envelope

- additional_vs_reducer_output_percent: `19.02%`
- percent_by_type: `{'decorator_call': '1.48%', 'direct_call_unresolved': '25.44%', 'dynamic_call': '5.03%', 'dynamic_member_call': '1.18%', 'member_call_unresolved': '66.86%'}`
- additional_vs_reducer_output_percent_by_language: `{'typescript': '19.02%'}`
- percent_by_type_by_language: `{'typescript': {'decorator_call': 1.4792899408284024, 'direct_call_unresolved': 25.443786982248522, 'dynamic_call': 5.029585798816568, 'dynamic_member_call': 1.183431952662722, 'member_call_unresolved': 66.86390532544378}}`

