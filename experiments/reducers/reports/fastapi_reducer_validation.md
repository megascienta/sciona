# SCIONA Reducer Validation Report

## Executive Summary

- repo=fastapi
- sampled_nodes=500
- reducer_precision_mean=0.6449579831932774
- reducer_recall_mean=0.8287910797618332
- db_precision_mean=0.6449579831932774
- db_recall_mean=0.8287910797618332
- thresholds_passed=False

## Aggregate Metrics

- reducer_in_contract_precision_mean: `0.6449579831932774`
- db_in_contract_precision_mean: `0.6449579831932774`
- reducer_in_contract_recall_mean: `0.8287910797618332`
- db_in_contract_recall_mean: `0.8287910797618332`
- reducer_misses_out_of_contract_rate: `0.7840670859538784`
- db_misses_out_of_contract_rate: `0.7840670859538784`
- reducer_coverage_node_rate: `1.0`
- db_coverage_node_rate: `1.0`
- reducer_coverage_file_rate: `1.0`
- db_coverage_file_rate: `1.0`
- reducer_stability_score: `1.0`
- db_stability_score: `1.0`

## Threshold Evaluation

- passed: `False`
- precision_mean 0.6449579831932774 < 0.95
- recall_mean 0.8287910797618332 < 0.9
- misses_out_of_contract_rate 0.7840670859538784 < 0.8
- group python::class precision 0.0 < 0.85
- group python::function precision 0.21428571428571427 < 0.85
- group python::function recall 0.042823379351740694 < 0.8
- group python::method precision 0.0 < 0.85

## Group Metrics

- reducer python::class: precision=`0.0`, recall=`None`
- reducer python::module: precision=`0.8885542168674698`, recall=`0.9755050505050504`
- reducer python::function: precision=`0.21428571428571427`, recall=`0.042823379351740694`
- reducer python::method: precision=`0.0`, recall=`None`
- db python::class: precision=`0.0`, recall=`None`
- db python::module: precision=`0.8885542168674698`, recall=`0.9755050505050504`
- db python::function: precision=`0.21428571428571427`, recall=`0.042823379351740694`
- db python::method: precision=`0.0`, recall=`None`

## Edge Type Breakdown

- reducer calls: tp=`10`, fp=`145`, fn=`193`
- reducer imports: tp=`330`, fp=`2603`, fn=`13`
- db calls: tp=`10`, fp=`145`, fn=`193`
- db imports: tp=`330`, fp=`2603`, fn=`13`

## Failure Examples

- fastapi.tests.test_schema_extra_examples.create_app: recall=0.0
- fastapi.tests.test_infer_param_optionality.test_openapi_schema: recall=0.0
- fastapi.tests.test_tutorial.test_bigger_applications.test_main.test_openapi_schema: recall=0.0
- fastapi.tests.test_response_model_as_return_annotation.test_openapi_schema: recall=0.0
- fastapi.tests.test_tutorial.test_additional_status_codes.test_tutorial001.get_client: recall=0.0
- fastapi.tests.test_extra_routes.test_openapi_schema: recall=0.0
- fastapi.datastructures: recall=0.0
- fastapi.tests.test_request_params.test_file.test_list.read_list_bytes: recall=0.0
- fastapi.tests.test_security_http_bearer.test_openapi_schema: recall=0.0
- fastapi.tests.test_request_params.test_body.test_required_str.read_model_required_alias: recall=0.0

## Failure Examples (DB vs Independent)

- fastapi.tests.test_schema_extra_examples.create_app: recall=0.0
- fastapi.tests.test_infer_param_optionality.test_openapi_schema: recall=0.0
- fastapi.tests.test_tutorial.test_bigger_applications.test_main.test_openapi_schema: recall=0.0
- fastapi.tests.test_response_model_as_return_annotation.test_openapi_schema: recall=0.0
- fastapi.tests.test_tutorial.test_additional_status_codes.test_tutorial001.get_client: recall=0.0
- fastapi.tests.test_extra_routes.test_openapi_schema: recall=0.0
- fastapi.datastructures: recall=0.0
- fastapi.tests.test_request_params.test_file.test_list.read_list_bytes: recall=0.0
- fastapi.tests.test_security_http_bearer.test_openapi_schema: recall=0.0
- fastapi.tests.test_request_params.test_body.test_required_str.read_model_required_alias: recall=0.0
