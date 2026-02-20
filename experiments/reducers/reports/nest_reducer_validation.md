# SCIONA Reducer Validation Report

## Executive Summary

- repo=nest
- sampled_nodes=500
- db_equivalence_precision_mean=1.0
- db_equivalence_recall_mean=1.0
- contract_precision_mean=0.6951223751462751
- contract_recall_mean=0.859211602363679
- full_precision_mean=0.7130797264369597
- full_recall_mean=0.7039707512817581
- thresholds_passed=False

## DB Equivalence (Reducer vs DB)

- precision_mean: `1.0`
- recall_mean: `1.0`
- coverage_node_rate: `1.0`
- empty_set_mismatch_count: `0`

## Independent Parser Totals

- raw_call_edges: `21028`
- raw_import_edges: `2064`
- normalized_call_edges: `21028`
- normalized_import_edges: `2064`
- in_contract_edges: `1338`
- out_of_contract_edges: `201`

## Independent Parser Coverage By Language

- typescript: files_parsed=`388`, files_total=`388`

## Contract Accuracy (Reducer vs Ground Truth In-Contract)

- in_contract_precision_mean: `0.6951223751462751`
- in_contract_recall_mean: `0.859211602363679`
- misses_out_of_contract_rate: `0.60625`
- coverage_node_rate: `1.0`
- coverage_file_rate: `1.0`
- stability_score: `1.0`

## Full Accuracy (Reducer vs Full Ground Truth)

- in_contract_precision_mean: `0.7130797264369597`
- in_contract_recall_mean: `0.7039707512817581`
- misses_out_of_contract_rate: `0.0`
- coverage_node_rate: `1.0`
- coverage_file_rate: `1.0`
- stability_score: `1.0`

## Threshold Evaluation (Contract)

- passed: `False`
- precision_mean 0.6951223751462751 < 0.95
- recall_mean 0.859211602363679 < 0.9
- misses_out_of_contract_rate 0.60625 < 0.8
- group typescript::module precision 0.7613768224669387 < 0.85
- group typescript::class precision 0.6381446986276045 < 0.85
- group typescript::function precision 0.6666666666666665 < 0.85
- group typescript::function recall 0.4698660714285714 < 0.8
- group typescript::method precision 0.3611111111111111 < 0.85
- group typescript::method recall 0.19318181818181818 < 0.8

## Group Metrics

- db_equivalence typescript::module: precision=`1.0`, recall=`1.0`
- db_equivalence typescript::class: precision=`1.0`, recall=`1.0`
- db_equivalence typescript::function: precision=`1.0`, recall=`1.0`
- db_equivalence typescript::method: precision=`1.0`, recall=`1.0`
- contract typescript::module: precision=`0.7613768224669387`, recall=`0.9986394557823131`
- contract typescript::class: precision=`0.6381446986276045`, recall=`0.9694752321867657`
- contract typescript::function: precision=`0.6666666666666665`, recall=`0.4698660714285714`
- contract typescript::method: precision=`0.3611111111111111`, recall=`0.19318181818181818`
- full typescript::module: precision=`0.7613768224669387`, recall=`0.8381847016943169`
- full typescript::class: precision=`0.6381446986276045`, recall=`0.9694752321867657`
- full typescript::function: precision=`0.68`, recall=`0.20024420024420025`
- full typescript::method: precision=`0.6388888888888888`, recall=`0.2119047619047619`

## Edge Type Breakdown

- db_equivalence calls: tp=`1012`, fp=`0`, fn=`0`
- db_equivalence imports: tp=`859`, fp=`0`, fn=`0`
- contract calls: tp=`559`, fp=`453`, fn=`125`
- contract imports: tp=`653`, fp=`206`, fn=`1`
- full calls: tp=`566`, fp=`446`, fn=`212`
- full imports: tp=`653`, fp=`206`, fn=`108`

## Out-of-Contract Breakdown

- import::typescript::relative_unresolved: `107`
- call::typescript::in_repo_unresolved: `86`
- call::typescript::dynamic: `8`
