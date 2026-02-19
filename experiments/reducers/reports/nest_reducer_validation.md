# SCIONA Reducer Validation Report

## Executive Summary

- repo=nest
- sampled_nodes=200
- precision_mean=0.0
- recall_mean=0.0
- thresholds_passed=False

## Aggregate Metrics

- in_contract_precision_mean: `0.0`
- in_contract_recall_mean: `0.0`
- misses_out_of_contract_rate: `0.0`
- coverage_node_rate: `0.485`
- coverage_file_rate: `1.1428571428571428`
- stability_score: `0.0`

## Threshold Evaluation

- passed: `False`
- precision_mean 0.0 < 0.95
- recall_mean 0.0 < 0.9
- misses_out_of_contract_rate 0.0 < 0.8
- group typescript::module precision 0.0 < 0.85
- group typescript::module recall 0.0 < 0.8

## Group Metrics

- typescript::module: precision=`0.0`, recall=`0.0`

## Edge Type Breakdown

- calls: tp=`0`, fp=`0`, fn=`0`
- imports: tp=`0`, fp=`598`, fn=`599`

## Failure Examples

- nest.packages.microservices.interfaces.microservice-configuration.interface: recall=0.0
- nest.packages.core.services.reflector.service: recall=0.0
- nest.packages.common.interfaces.microservices.nest-microservice-options.interface: recall=0.0
- nest.packages.microservices.listener-metadata-explorer: recall=0.0
- nest.sample.05-sql-typeorm.src.users.users.controller.spec: recall=0.0
- nest.packages.microservices.external.kafka.interface: recall=0.0
- nest.packages.microservices.tokens: recall=0.0
- nest.packages.microservices.test.server.server-grpc.spec: recall=0.0
- nest.packages.core.test.router.router-execution-context.spec: recall=0.0
- nest.packages.core.nest-application: recall=0.0
