# SCIONA Reducer Validation Report

## Q1. Reducers vs DB Correctness

- pass: `True`
- exact_required: `True`
- reference/candidate/intersection: `1122`/`1122`/`1122`
- missing/spillover: `0`/`0`
- mismatch_nodes: `0`

## Q2. Reducers vs Independent Within Static Contract

- pass: `False`
- target_mutual_accuracy_min: `0.990000`
- target_missing_rate_max: `0.010000`
- target_spillover_rate_max: `0.010000`
- scored_nodes: `274`
- avg_missing_rate/avg_spillover_rate: `0.083637`/`0.029197`
- avg_mutual_accuracy: `0.902859`
- reference/candidate/intersection: `1094`/`1065`/`1052`
- missing/spillover: `42`/`13`
- filtering_source: `core_only`
- by_language: `{'java': {'scored_nodes': 133, 'avg_missing_rate': 0.11215538847117794, 'avg_spillover_rate': 0.02631578947368421, 'avg_mutual_accuracy': 0.8758145363408522, 'pass': False}, 'python': {'scored_nodes': 136, 'avg_missing_rate': 0.058823529411764705, 'avg_spillover_rate': 0.03308823529411765, 'avg_mutual_accuracy': 0.9257352941176471, 'pass': False}, 'typescript': {'scored_nodes': 5, 'avg_missing_rate': 0.0, 'avg_spillover_rate': 0.0, 'avg_mutual_accuracy': 1.0, 'pass': True}}`

## Q3. Beyond Static Contract Envelope

- scored_nodes: `274`
- avg_out_of_contract_rate_percent: `44.25%`
- avg_percent_by_type: `{'decorator_call': '3.89%', 'direct_call_unresolved': '25.36%', 'member_call_unresolved': '14.99%'}`

