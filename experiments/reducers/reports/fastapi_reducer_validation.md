# SCIONA Reducer Validation Report

## Executive Summary

- repo=fastapi
- sampled_nodes=200
- precision_mean=0.6822464621148832
- recall_mean=0.2314106816755121
- thresholds_passed=False

## Aggregate Metrics

- in_contract_precision_mean: `0.6822464621148832`
- in_contract_recall_mean: `0.2314106816755121`
- misses_out_of_contract_rate: `0.0`
- coverage_node_rate: `0.835`
- coverage_file_rate: `1.3333333333333333`
- stability_score: `1.0`

## Threshold Evaluation

- passed: `False`
- precision_mean 0.6822464621148832 < 0.95
- recall_mean 0.2314106816755121 < 0.9
- misses_out_of_contract_rate 0.0 < 0.8
- group python::module precision 0.6822464621148832 < 0.85
- group python::module recall 0.4075591110106034 < 0.8
- group python::function recall 0.0 < 0.8

## Group Metrics

- python::module: precision=`0.6822464621148832`, recall=`0.4075591110106034`
- python::function: precision=`None`, recall=`0.0`
- python::method: precision=`None`, recall=`None`

## Edge Type Breakdown

- calls: tp=`0`, fp=`0`, fn=`345`
- imports: tp=`159`, fp=`1171`, fn=`298`

## Failure Examples

- fastapi.tests.test_tutorial.test_generate_clients.test_tutorial004: recall=0.0
- fastapi.param_functions.Path: recall=0.0
- fastapi.tests.test_application.test_openapi_schema: recall=0.0
- fastapi.encoders.jsonable_encoder: recall=0.0
- fastapi.responses: recall=0.0
- fastapi.tests.test_tutorial.test_body_multiple_params.test_tutorial004.test_put_all: recall=0.0
- fastapi.tests.test_additional_properties_bool.test_openapi_schema: recall=0.0
- fastapi.tests.test_tutorial.test_sql_databases.test_tutorial002.test_openapi_schema: recall=0.0
- fastapi.tests.test_infer_param_optionality.test_openapi_schema: recall=0.0
- fastapi.websockets: recall=0.0
