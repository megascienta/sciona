# SCIONA Reducer Validation Report

## Executive Summary

- repo=commons_lang
- sampled_nodes=500
- db_equivalence_precision_mean=1.0
- db_equivalence_recall_mean=1.0
- contract_precision_mean=0.5631539981642604
- contract_recall_mean=0.5716818362358935
- full_precision_mean=0.7491721672280461
- full_recall_mean=0.5009789589829778
- thresholds_passed=False

## DB Equivalence (Reducer vs DB)

- precision_mean: `1.0`
- recall_mean: `1.0`
- coverage_node_rate: `1.0`
- empty_set_mismatch_count: `0`

## Independent Parser Totals

- raw_call_edges: `71527`
- raw_import_edges: `2628`
- normalized_call_edges: `71527`
- normalized_import_edges: `2628`
- in_contract_edges: `18152`
- out_of_contract_edges: `12363`

## Independent Parser Coverage By Language

- java: files_parsed=`288`, files_total=`288`

## Contract Accuracy (Reducer vs Ground Truth In-Contract)

- in_contract_precision_mean: `0.5631539981642604`
- in_contract_recall_mean: `0.5716818362358935`
- misses_out_of_contract_rate: `0.3960720747889023`
- coverage_node_rate: `1.0`
- coverage_file_rate: `1.0`
- stability_score: `1.0`

## Full Accuracy (Reducer vs Full Ground Truth)

- in_contract_precision_mean: `0.7491721672280461`
- in_contract_recall_mean: `0.5009789589829778`
- misses_out_of_contract_rate: `0.0`
- coverage_node_rate: `1.0`
- coverage_file_rate: `1.0`
- stability_score: `1.0`

## Threshold Evaluation (Contract)

- passed: `False`
- precision_mean 0.5631539981642604 < 0.95
- recall_mean 0.5716818362358935 < 0.9
- misses_out_of_contract_rate 0.3960720747889023 < 0.8
- group java::class precision 0.4322510069670915 < 0.85
- group java::class recall 0.2688446793530089 < 0.8
- group java::module precision 0.7528263403263403 < 0.85
- group java::method precision 0.4853658536585366 < 0.85
- group java::method recall 0.2732220842993201 < 0.8

## Group Metrics

- db_equivalence java::class: precision=`1.0`, recall=`1.0`
- db_equivalence java::module: precision=`1.0`, recall=`1.0`
- db_equivalence java::method: precision=`1.0`, recall=`1.0`
- contract java::class: precision=`0.4322510069670915`, recall=`0.2688446793530089`
- contract java::module: precision=`0.7528263403263403`, recall=`1.0`
- contract java::method: precision=`0.4853658536585366`, recall=`0.2732220842993201`
- full java::class: precision=`0.7262515352376296`, recall=`0.21139196601066157`
- full java::module: precision=`0.7528263403263403`, recall=`1.0`
- full java::method: precision=`0.8292682926829268`, recall=`0.21139086846558922`

## Edge Type Breakdown

- db_equivalence calls: tp=`3855`, fp=`0`, fn=`0`
- db_equivalence imports: tp=`298`, fp=`0`, fn=`0`
- contract calls: tp=`1883`, fp=`1972`, fn=`16021`
- contract imports: tp=`248`, fp=`50`, fn=`0`
- full calls: tp=`2752`, fp=`1103`, fn=`27515`
- full imports: tp=`248`, fp=`50`, fn=`0`

## Out-of-Contract Breakdown

- call::java::in_repo_unresolved: `12360`
- call::java::dynamic: `3`
