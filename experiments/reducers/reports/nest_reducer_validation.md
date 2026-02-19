# SCIONA Reducer Validation Report

## Executive Summary

- repo=nest
- sampled_nodes=500
- db_equivalence_precision_mean=1.0
- db_equivalence_recall_mean=1.0
- contract_precision_mean=0.8476119395422944
- contract_recall_mean=0.9041909071710538
- full_precision_mean=0.9218226497255505
- full_recall_mean=0.309084655754836
- thresholds_passed=False

## DB Equivalence (Reducer vs DB)

- precision_mean: `1.0`
- recall_mean: `1.0`
- coverage_node_rate: `1.0`
- empty_set_mismatch_count: `0`

## Independent Parser Totals

- raw_call_edges: `21565`
- raw_import_edges: `2193`
- normalized_call_edges: `21565`
- normalized_import_edges: `2193`
- in_contract_edges: `1422`
- out_of_contract_edges: `2962`

## Independent Parser Coverage By Language

- typescript: files_parsed=`394`, files_total=`394`

## Contract Accuracy (Reducer vs Ground Truth In-Contract)

- in_contract_precision_mean: `0.8476119395422944`
- in_contract_recall_mean: `0.9041909071710538`
- misses_out_of_contract_rate: `0.954064892453518`
- coverage_node_rate: `1.0`
- coverage_file_rate: `1.0`
- stability_score: `1.0`

## Full Accuracy (Reducer vs Full Ground Truth)

- in_contract_precision_mean: `0.9218226497255505`
- in_contract_recall_mean: `0.309084655754836`
- misses_out_of_contract_rate: `0.0`
- coverage_node_rate: `1.0`
- coverage_file_rate: `1.0`
- stability_score: `1.0`

## Threshold Evaluation (Contract)

- passed: `False`
- precision_mean 0.8476119395422944 < 0.95
- group typescript::method precision 0.5030864197530863 < 0.85
- group typescript::method recall 0.5051282051282052 < 0.8
- group typescript::class precision 0.48740317608509587 < 0.85

## Group Metrics

- db_equivalence typescript::method: precision=`1.0`, recall=`1.0`
- db_equivalence typescript::function: precision=`1.0`, recall=`1.0`
- db_equivalence typescript::module: precision=`1.0`, recall=`1.0`
- db_equivalence typescript::class: precision=`1.0`, recall=`1.0`
- contract typescript::method: precision=`0.5030864197530863`, recall=`0.5051282051282052`
- contract typescript::function: precision=`0.9404761904761905`, recall=`0.8997023809523809`
- contract typescript::module: precision=`1.0`, recall=`0.9987179487179488`
- contract typescript::class: precision=`0.48740317608509587`, recall=`0.8044040695649892`
- full typescript::method: precision=`0.8518518518518519`, recall=`0.2114458874458874`
- full typescript::function: precision=`0.9523809523809523`, recall=`0.20311948853615513`
- full typescript::module: precision=`1.0`, recall=`0.4076389669815753`
- full typescript::class: precision=`0.6945696338088613`, recall=`0.19773354516652553`

## Edge Type Breakdown

- db_equivalence calls: tp=`1381`, fp=`0`, fn=`0`
- db_equivalence imports: tp=`664`, fp=`0`, fn=`0`
- contract calls: tp=`632`, fp=`749`, fn=`125`
- contract imports: tp=`664`, fp=`0`, fn=`1`
- full calls: tp=`925`, fp=`456`, fn=`2010`
- full imports: tp=`664`, fp=`0`, fn=`785`

## Out-of-Contract Breakdown

- import::typescript::external: `670`
- import::typescript::relative_unresolved: `114`
- call::typescript::in_repo_unresolved: `848`
- call::typescript::external: `1134`
- call::typescript::standard_call: `172`
- call::typescript::dynamic: `24`
