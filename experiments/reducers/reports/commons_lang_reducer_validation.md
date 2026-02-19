# SCIONA Reducer Validation Report

## Executive Summary

- repo=commons_lang
- sampled_nodes=500
- db_equivalence_precision_mean=1.0
- db_equivalence_recall_mean=1.0
- contract_precision_mean=0.5632926800290752
- contract_recall_mean=0.5876666870434354
- full_precision_mean=0.7544842640479975
- full_recall_mean=0.15519385217408324
- thresholds_passed=False

## DB Equivalence (Reducer vs DB)

- precision_mean: `1.0`
- recall_mean: `1.0`
- coverage_node_rate: `1.0`
- empty_set_mismatch_count: `0`

## Independent Parser Totals

- raw_call_edges: `71165`
- raw_import_edges: `2598`
- normalized_call_edges: `71165`
- normalized_import_edges: `2598`
- in_contract_edges: `19072`
- out_of_contract_edges: `36667`

## Independent Parser Coverage By Language

- java: files_parsed=`291`, files_total=`291`

## Contract Accuracy (Reducer vs Ground Truth In-Contract)

- in_contract_precision_mean: `0.5632926800290752`
- in_contract_recall_mean: `0.5876666870434354`
- misses_out_of_contract_rate: `0.6991551117758823`
- coverage_node_rate: `1.0`
- coverage_file_rate: `1.0`
- stability_score: `1.0`

## Full Accuracy (Reducer vs Full Ground Truth)

- in_contract_precision_mean: `0.7544842640479975`
- in_contract_recall_mean: `0.15519385217408324`
- misses_out_of_contract_rate: `0.0`
- coverage_node_rate: `1.0`
- coverage_file_rate: `1.0`
- stability_score: `1.0`

## Threshold Evaluation (Contract)

- passed: `False`
- precision_mean 0.5632926800290752 < 0.95
- recall_mean 0.5876666870434354 < 0.9
- misses_out_of_contract_rate 0.6991551117758823 < 0.8
- group java::class precision 0.56459446558912 < 0.85
- group java::class recall 0.5915927783201239 < 0.8
- group java::method precision 0.5598958333333334 < 0.85
- group java::method recall 0.575692108649536 < 0.8

## Group Metrics

- db_equivalence java::class: precision=`1.0`, recall=`1.0`
- db_equivalence java::module: precision=`None`, recall=`None`
- db_equivalence java::method: precision=`1.0`, recall=`1.0`
- contract java::class: precision=`0.56459446558912`, recall=`0.5915927783201239`
- contract java::module: precision=`None`, recall=`None`
- contract java::method: precision=`0.5598958333333334`, recall=`0.575692108649536`
- full java::class: precision=`0.7576997903897448`, recall=`0.2989521661447953`
- full java::module: precision=`None`, recall=`0.0`
- full java::method: precision=`0.74609375`, recall=`0.34390656931620234`

## Edge Type Breakdown

- db_equivalence calls: tp=`6736`, fp=`0`, fn=`0`
- db_equivalence imports: tp=`0`, fp=`0`, fn=`0`
- contract calls: tp=`4188`, fp=`2548`, fn=`14884`
- contract imports: tp=`0`, fp=`0`, fn=`0`
- full calls: tp=`5101`, fp=`1635`, fn=`48568`
- full imports: tp=`0`, fp=`0`, fn=`2070`

## Out-of-Contract Breakdown

- import::java::external: `2070`
- call::java::external: `21101`
- call::java::standard_call: `741`
- call::java::in_repo_unresolved: `12752`
- call::java::dynamic: `3`
