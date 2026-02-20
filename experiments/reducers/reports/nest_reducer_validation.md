# SCIONA Reducer Validation Report

## Executive Summary

- repo=nest
- sampled_nodes=500
- db_equivalence_precision_mean=1.0
- db_equivalence_recall_mean=1.0
- contract_precision_mean=0.7581819269852612
- contract_recall_mean=0.7477147063675832
- full_precision_mean=0.8237545313764827
- full_recall_mean=0.572261943902241
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
- in_contract_edges: `1384`
- out_of_contract_edges: `787`

## Independent Parser Coverage By Language

- typescript: files_parsed=`388`, files_total=`388`

## Contract Accuracy (Reducer vs Ground Truth In-Contract)

- in_contract_precision_mean: `0.7581819269852612`
- in_contract_recall_mean: `0.7477147063675832`
- misses_out_of_contract_rate: `0.5118613138686131`
- coverage_node_rate: `1.0`
- coverage_file_rate: `1.0`
- stability_score: `1.0`

## Full Accuracy (Reducer vs Full Ground Truth)

- in_contract_precision_mean: `0.8237545313764827`
- in_contract_recall_mean: `0.572261943902241`
- misses_out_of_contract_rate: `0.0`
- coverage_node_rate: `1.0`
- coverage_file_rate: `1.0`
- stability_score: `1.0`

## Threshold Evaluation (Contract)

- passed: `False`
- precision_mean 0.7581819269852612 < 0.95
- recall_mean 0.7477147063675832 < 0.9
- misses_out_of_contract_rate 0.5118613138686131 < 0.8
- group typescript::class precision 0.3405434869105745 < 0.85
- group typescript::class recall 0.3388392566604641 < 0.8
- group typescript::function precision 0.6666666666666665 < 0.85
- group typescript::function recall 0.45944940476190477 < 0.8
- group typescript::method precision 0.38235294117647056 < 0.85
- group typescript::method recall 0.17803030303030304 < 0.8

## Group Metrics

- db_equivalence typescript::module: precision=`1.0`, recall=`1.0`
- db_equivalence typescript::class: precision=`1.0`, recall=`1.0`
- db_equivalence typescript::function: precision=`1.0`, recall=`1.0`
- db_equivalence typescript::method: precision=`1.0`, recall=`1.0`
- contract typescript::module: precision=`0.9423076923076923`, recall=`0.9986394557823131`
- contract typescript::class: precision=`0.3405434869105745`, recall=`0.3388392566604641`
- contract typescript::function: precision=`0.6666666666666665`, recall=`0.45944940476190477`
- contract typescript::method: precision=`0.38235294117647056`, recall=`0.17803030303030304`
- full typescript::module: precision=`0.9423076923076923`, recall=`0.8381847016943169`
- full typescript::class: precision=`0.5863253066378067`, recall=`0.2679899555771194`
- full typescript::function: precision=`0.68`, recall=`0.1916971916971917`
- full typescript::method: precision=`0.6176470588235294`, recall=`0.1761904761904762`

## Edge Type Breakdown

- db_equivalence calls: tp=`739`, fp=`0`, fn=`0`
- db_equivalence imports: tp=`703`, fp=`0`, fn=`0`
- contract calls: tp=`196`, fp=`543`, fn=`534`
- contract imports: tp=`653`, fp=`50`, fn=`1`
- full calls: tp=`386`, fp=`353`, fn=`1024`
- full imports: tp=`653`, fp=`50`, fn=`108`

## Out-of-Contract Breakdown

- import::typescript::relative_unresolved: `107`
- call::typescript::in_repo_unresolved: `654`
- call::typescript::dynamic: `26`
