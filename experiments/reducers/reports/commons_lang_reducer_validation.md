# SCIONA Reducer Validation Report

## Executive Summary

- repo=commons_lang
- sampled_nodes=500
- db_equivalence_precision_mean=1.0
- db_equivalence_recall_mean=1.0
- contract_precision_mean=0.7069641036398031
- contract_recall_mean=0.86389156933284
- full_precision_mean=0.7326397793154787
- full_recall_mean=0.8224404341287685
- thresholds_passed=False

## DB Equivalence (Reducer vs DB)

- precision_mean: `1.0`
- recall_mean: `1.0`
- coverage_node_rate: `1.0`
- empty_set_mismatch_count: `0`

## Independent Parser Totals

- raw_call_edges: `72553`
- raw_import_edges: `2710`
- normalized_call_edges: `72553`
- normalized_import_edges: `2710`
- in_contract_edges: `8129`
- out_of_contract_edges: `287`

## Independent Parser Coverage By Language

- java: files_parsed=`295`, files_total=`295`

## Contract Accuracy (Reducer vs Ground Truth In-Contract)

- in_contract_precision_mean: `0.7069641036398031`
- in_contract_recall_mean: `0.86389156933284`
- misses_out_of_contract_rate: `0.058511863625892654`
- coverage_node_rate: `1.0`
- coverage_file_rate: `1.0`
- stability_score: `1.0`

## Full Accuracy (Reducer vs Full Ground Truth)

- in_contract_precision_mean: `0.7326397793154787`
- in_contract_recall_mean: `0.8224404341287685`
- misses_out_of_contract_rate: `0.0`
- coverage_node_rate: `1.0`
- coverage_file_rate: `1.0`
- stability_score: `1.0`

## Threshold Evaluation (Contract)

- passed: `False`
- precision_mean 0.7069641036398031 < 0.95
- recall_mean 0.86389156933284 < 0.9
- misses_out_of_contract_rate 0.058511863625892654 < 0.8
- group java::method precision 0.6111111111111112 < 0.85
- group java::method recall 0.3908335768378503 < 0.8
- group java::module precision 0.7713986883763002 < 0.85
- group java::class precision 0.6843418539492295 < 0.85

## Group Metrics

- db_equivalence java::method: precision=`1.0`, recall=`1.0`
- db_equivalence java::module: precision=`1.0`, recall=`1.0`
- db_equivalence java::class: precision=`1.0`, recall=`1.0`
- contract java::method: precision=`0.6111111111111112`, recall=`0.3908335768378503`
- contract java::module: precision=`0.7713986883763002`, recall=`1.0`
- contract java::class: precision=`0.6843418539492295`, recall=`0.8800955870156643`
- full java::method: precision=`0.8222222222222222`, recall=`0.29255580522049557`
- full java::module: precision=`0.7713986883763002`, recall=`1.0`
- full java::class: precision=`0.6843418539492295`, recall=`0.8800955870156643`

## Edge Type Breakdown

- db_equivalence calls: tp=`5131`, fp=`0`, fn=`0`
- db_equivalence imports: tp=`310`, fp=`0`, fn=`0`
- contract calls: tp=`3782`, fp=`1349`, fn=`4087`
- contract imports: tp=`260`, fp=`50`, fn=`0`
- full calls: tp=`3799`, fp=`1332`, fn=`4357`
- full imports: tp=`260`, fp=`50`, fn=`0`

## Out-of-Contract Breakdown

- call::java::in_repo_unresolved: `287`
