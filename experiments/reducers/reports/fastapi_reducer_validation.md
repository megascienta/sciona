# SCIONA Reducer Validation Report

## Executive Summary

- repo=fastapi
- sampled_nodes=500
- db_equivalence_precision_mean=1.0
- db_equivalence_recall_mean=1.0
- contract_precision_mean=0.8682844612143757
- contract_recall_mean=0.7634695157717803
- full_precision_mean=0.9776594612143757
- full_recall_mean=0.6066414745550394
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
- in_contract_edges: `3218`
- out_of_contract_edges: `177`

## Independent Parser Coverage By Language

- python: files_parsed=`1284`, files_total=`1284`

## Contract Accuracy (Reducer vs Ground Truth In-Contract)

- in_contract_precision_mean: `0.8682844612143757`
- in_contract_recall_mean: `0.7634695157717803`
- misses_out_of_contract_rate: `0.3048780487804878`
- coverage_node_rate: `1.0`
- coverage_file_rate: `1.0`
- stability_score: `1.0`

## Full Accuracy (Reducer vs Full Ground Truth)

- in_contract_precision_mean: `0.9776594612143757`
- in_contract_recall_mean: `0.6066414745550394`
- misses_out_of_contract_rate: `0.0`
- coverage_node_rate: `1.0`
- coverage_file_rate: `1.0`
- stability_score: `1.0`

## Threshold Evaluation (Contract)

- passed: `False`
- precision_mean 0.8682844612143757 < 0.95
- recall_mean 0.7634695157717803 < 0.9
- misses_out_of_contract_rate 0.3048780487804878 < 0.8
- group python::function precision 0.5454545454545454 < 0.85
- group python::function recall 0.34482758620689663 < 0.8
- group python::method precision 0.2708333333333333 < 0.85
- group python::method recall 0.1388888888888889 < 0.8

## Group Metrics

- db_equivalence python::module: precision=`1.0`, recall=`1.0`
- db_equivalence python::function: precision=`1.0`, recall=`1.0`
- db_equivalence python::method: precision=`1.0`, recall=`1.0`
- db_equivalence python::class: precision=`1.0`, recall=`1.0`
- contract python::module: precision=`0.9938007364939516`, recall=`0.9643920959083114`
- contract python::function: precision=`0.5454545454545454`, recall=`0.34482758620689663`
- contract python::method: precision=`0.2708333333333333`, recall=`0.1388888888888889`
- contract python::class: precision=`0.9375`, recall=`1.0`
- full python::module: precision=`0.9938007364939516`, recall=`0.964381727383389`
- full python::function: precision=`0.9090909090909091`, recall=`0.16569183504667379`
- full python::method: precision=`0.9583333333333334`, recall=`0.1923472008217771`
- full python::class: precision=`0.9375`, recall=`1.0`

## Edge Type Breakdown

- db_equivalence calls: tp=`134`, fp=`0`, fn=`0`
- db_equivalence imports: tp=`2853`, fp=`0`, fn=`0`
- contract calls: tp=`88`, fp=`46`, fn=`145`
- contract imports: tp=`2845`, fp=`8`, fn=`140`
- full calls: tp=`127`, fp=`7`, fn=`280`
- full imports: tp=`2845`, fp=`8`, fn=`143`

## Out-of-Contract Breakdown

- call::python::in_repo_unresolved: `168`
- import::python::relative_unresolved: `2`
- import::python::in_repo_unresolved: `1`
- call::python::dynamic: `6`
