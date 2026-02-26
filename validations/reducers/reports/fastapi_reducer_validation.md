# SCIONA Reducer Validation Report

## Q1. Reducers vs DB Correctness

- pass: `True`
- exact_required: `True`
- reference/candidate/intersection: `2971`/`2971`/`2971`
- missing/spillover: `0`/`0`
- mismatch_nodes: `0`

## Q2. Reducers vs Independent Within Static Contract

- pass: `False`
- target_mutual_accuracy_min: `0.990000`
- target_missing_rate_max: `0.010000`
- target_spillover_rate_max: `0.010000`
- scored_nodes: `235`
- avg_missing_rate/avg_spillover_rate: `0.200018`/`0.003033`
- avg_mutual_accuracy: `0.797533`
- reference/candidate/intersection: `2969`/`2931`/`2909`
- missing/spillover: `60`/`22`
- filtering_source: `core_only`
- by_language: `{'python': {'scored_nodes': 235, 'avg_missing_rate': 0.2000182156935312, 'avg_spillover_rate': 0.003033161862890377, 'avg_mutual_accuracy': 0.7975332968969389, 'pass': False}}`

## Q3. Beyond Static Contract Envelope

- scored_nodes: `235`
- avg_out_of_contract_rate_percent: `15.53%`
- avg_percent_by_type: `{'decorator_call': '7.45%', 'direct_call_unresolved': '0.64%', 'dynamic_call': '0.64%', 'member_call_unresolved': '6.38%', 'module_import_unresolved': '0.00%', 'relative_import_unresolved': '0.43%'}`

