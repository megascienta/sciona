# SCIONA Reducer Validation Report

## Executive Summary

- repo=fastapi
- sampled_nodes=500
- db_equivalence_precision_mean=1.0
- db_equivalence_recall_mean=1.0
- contract_precision_mean=0.8334463966279574
- contract_recall_mean=0.8234731319134079
- full_precision_mean=0.9774414725902465
- full_recall_mean=0.23608318282444224
- thresholds_passed=False

## DB Equivalence (Reducer vs DB)

- precision_mean: `1.0`
- recall_mean: `1.0`
- coverage_node_rate: `1.0`
- empty_set_mismatch_count: `0`

## Independent Parser Totals

- raw_call_edges: `15400`
- raw_import_edges: `3702`
- normalized_call_edges: `15400`
- normalized_import_edges: `3702`
- in_contract_edges: `3303`
- out_of_contract_edges: `6073`

## Independent Parser Coverage By Language

- python: files_parsed=`1284`, files_total=`1284`

## Contract Accuracy (Reducer vs Ground Truth In-Contract)

- in_contract_precision_mean: `0.8334463966279574`
- in_contract_recall_mean: `0.8234731319134079`
- misses_out_of_contract_rate: `0.9483881213276163`
- coverage_node_rate: `1.0`
- coverage_file_rate: `1.0`
- stability_score: `1.0`

## Full Accuracy (Reducer vs Full Ground Truth)

- in_contract_precision_mean: `0.9774414725902465`
- in_contract_recall_mean: `0.23608318282444224`
- misses_out_of_contract_rate: `0.0`
- coverage_node_rate: `1.0`
- coverage_file_rate: `1.0`
- stability_score: `1.0`

## Threshold Evaluation (Contract)

- passed: `False`
- precision_mean 0.8334463966279574 < 0.95
- recall_mean 0.8234731319134079 < 0.9
- group python::function precision 0.7058823529411765 < 0.85
- group python::function recall 0.6627604166666667 < 0.8
- group python::method precision 0.38139534883720927 < 0.85
- group python::method recall 0.38695838695838697 < 0.8
- group python::class precision 0.49304029304029307 < 0.85
- group python::class recall 0.49425872093023254 < 0.8

## Group Metrics

- db_equivalence python::module: precision=`1.0`, recall=`1.0`
- db_equivalence python::function: precision=`1.0`, recall=`1.0`
- db_equivalence python::method: precision=`1.0`, recall=`1.0`
- db_equivalence python::class: precision=`1.0`, recall=`1.0`
- contract python::module: precision=`0.9907143167408652`, recall=`0.9613433154205066`
- contract python::function: precision=`0.7058823529411765`, recall=`0.6627604166666667`
- contract python::method: precision=`0.38139534883720927`, recall=`0.38695838695838697`
- contract python::class: precision=`0.49304029304029307`, recall=`0.49425872093023254`
- full python::module: precision=`0.9907143167408652`, recall=`0.3756651863402974`
- full python::function: precision=`0.9117647058823529`, recall=`0.06763066110278379`
- full python::method: precision=`0.9767441860465116`, recall=`0.11990450232637735`
- full python::class: precision=`1.0`, recall=`0.06405262246233492`

## Edge Type Breakdown

- db_equivalence calls: tp=`177`, fp=`0`, fn=`0`
- db_equivalence imports: tp=`2899`, fp=`0`, fn=`0`
- contract calls: tp=`88`, fp=`89`, fn=`184`
- contract imports: tp=`2890`, fp=`9`, fn=`141`
- full calls: tp=`166`, fp=`11`, fn=`2028`
- full imports: tp=`2890`, fp=`9`, fn=`4292`

## Out-of-Contract Breakdown

- import::python::external: `4148`
- call::python::external: `1616`
- call::python::standard_call: `82`
- call::python::in_repo_unresolved: `214`
- call::python::dynamic: `10`
- import::python::relative_unresolved: `2`
- import::python::in_repo_unresolved: `1`
