# SCIONA Reducer Validation Report

## Q1. Reducers vs DB Correctness

- pass: `True`
- exact_required: `True`
- tp/fp/fn: `4909`/`0`/`0`
- mismatch_nodes: `0`

## Q2. Reducers vs Independent Within Static Contract

- pass: `False`
- target: `0.990000`
- precision/recall: `0.986732`/`0.993016`
- fp/fn: `65`/`34`
- contract_truth_edges: `4868`
- filtering_source: `core_only`
- by_language: `{'java': {'tp': 4834, 'fp': 65, 'fn': 34, 'precision': 0.9867319861196162, 'recall': 0.9930156121610517, 'pass': False}}`
- top_mismatch_signatures_count: `20`

## Q3. Beyond Static Contract Envelope

- additional_vs_reducer_output_percent: `4.85%`
- percent_by_type: `{'direct_call_unresolved': '100.00%'}`
- additional_vs_reducer_output_percent_by_language: `{'java': '4.85%'}`
- percent_by_type_by_language: `{'java': {'direct_call_unresolved': 100.0}}`

