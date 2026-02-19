# SCIONA Reducer Validation Report

## Executive Summary

- repo=nest
- sampled_nodes=500
- reducer_precision_mean=0.625575851972546
- reducer_recall_mean=0.4527972685713036
- db_precision_mean=0.625575851972546
- db_recall_mean=0.4527972685713036
- thresholds_passed=False

## Aggregate Metrics

- reducer_in_contract_precision_mean: `0.625575851972546`
- db_in_contract_precision_mean: `0.625575851972546`
- reducer_in_contract_recall_mean: `0.4527972685713036`
- db_in_contract_recall_mean: `0.4527972685713036`
- reducer_misses_out_of_contract_rate: `0.3419391853126793`
- db_misses_out_of_contract_rate: `0.3419391853126793`
- reducer_coverage_node_rate: `1.0`
- db_coverage_node_rate: `1.0`
- reducer_coverage_file_rate: `1.0`
- db_coverage_file_rate: `1.0`
- reducer_stability_score: `1.0`
- db_stability_score: `1.0`

## Threshold Evaluation

- passed: `False`
- precision_mean 0.625575851972546 < 0.95
- recall_mean 0.4527972685713036 < 0.9
- misses_out_of_contract_rate 0.3419391853126793 < 0.8
- group typescript::module precision 0.37071657732948066 < 0.85
- group typescript::function recall 0.17482887166755928 < 0.8
- group typescript::method recall 0.29464265591294 < 0.8
- group typescript::class recall 0.32090435352926056 < 0.8

## Group Metrics

- reducer typescript::module: precision=`0.37071657732948066`, recall=`0.9366648933722104`
- reducer typescript::function: precision=`0.9868421052631579`, recall=`0.17482887166755928`
- reducer typescript::method: precision=`0.96875`, recall=`0.29464265591294`
- reducer typescript::class: precision=`0.8897454449681416`, recall=`0.32090435352926056`
- db typescript::module: precision=`0.37071657732948066`, recall=`0.9366648933722104`
- db typescript::function: precision=`0.9868421052631579`, recall=`0.17482887166755928`
- db typescript::method: precision=`0.96875`, recall=`0.29464265591294`
- db typescript::class: precision=`0.8897454449681416`, recall=`0.32090435352926056`

## Edge Type Breakdown

- reducer calls: tp=`1329`, fp=`67`, fn=`2276`
- reducer imports: tp=`245`, fp=`439`, fn=`18`
- db calls: tp=`1329`, fp=`67`, fn=`2276`
- db imports: tp=`245`, fp=`439`, fn=`18`

## Failure Examples

- nest.packages.testing.testing-injector: recall=0.0
- nest.integration.hello-world.e2e.exclude-middleware-fastify.spec.TestController.noMiddleware: recall=0.0
- nest.tools.benchmarks.src.main.fmtPct: recall=0.0
- nest.packages.common.pipes.validation.pipe.ValidationPipe.toEmptyIfNil: recall=0.0
- nest.sample.03-microservices.src.common.interceptors.logging.interceptor.LoggingInterceptor: recall=0.0
- nest.packages.microservices.test.json-socket.helpers.range: recall=0.0
- nest.tools.benchmarks.src.main.sleep: recall=0.0
- nest.integration.inspector.src.circular-hello.interceptors.logging.interceptor.Interceptor.intercept: recall=0.0
- nest.integration.nest-application.get-url.e2e.utils.randomPort: recall=0.0
- nest.integration.hello-world.e2e.exclude-middleware.spec.TestController: recall=0.0

## Failure Examples (DB vs Independent)

- nest.packages.testing.testing-injector: recall=0.0
- nest.integration.hello-world.e2e.exclude-middleware-fastify.spec.TestController.noMiddleware: recall=0.0
- nest.tools.benchmarks.src.main.fmtPct: recall=0.0
- nest.packages.common.pipes.validation.pipe.ValidationPipe.toEmptyIfNil: recall=0.0
- nest.sample.03-microservices.src.common.interceptors.logging.interceptor.LoggingInterceptor: recall=0.0
- nest.packages.microservices.test.json-socket.helpers.range: recall=0.0
- nest.tools.benchmarks.src.main.sleep: recall=0.0
- nest.integration.inspector.src.circular-hello.interceptors.logging.interceptor.Interceptor.intercept: recall=0.0
- nest.integration.nest-application.get-url.e2e.utils.randomPort: recall=0.0
- nest.integration.hello-world.e2e.exclude-middleware.spec.TestController: recall=0.0
