# SCIONA Reducer Validation Report

## Sampling

- seed: `20260219`
- requested_nodes: `500`
- sampled_nodes: `500`
- population_by_language: `{'typescript': 6724}`
- population_by_kind: `{'class': 1669, 'function': 289, 'method': 3107, 'module': 1659}`
- sampled_by_language: `{'typescript': 500}`
- sampled_by_kind: `{'class': 125, 'function': 125, 'method': 125, 'module': 125}`

## Q1. Reducers vs DB Correctness

- pass: `True`
- exact_required: `True`
- reference/candidate/intersection: `1819`/`1819`/`1819`
- missing/spillover: `0`/`0`
- mismatch_nodes: `0`

## Q2. Reducers vs Independent Within Static Contract

- pass: `False`
- target_mutual_accuracy_min: `0.990000`
- target_missing_rate_max: `0.010000`
- target_spillover_rate_max: `0.010000`
- metric_mode: `weighted_aggregate_v2`
- scored_nodes: `314`
- avg_missing_rate/avg_spillover_rate: `0.086131`/`0.000112`
- avg_mutual_accuracy: `0.913761`
- weighted_missing_rate/weighted_spillover_rate: `0.031126`/`0.003396`
- weighted_mutual_accuracy: `0.965595`
- reference/candidate/intersection: `1767`/`1718`/`1712`
- missing/spillover: `55`/`6`
- filtering_source: `core_only`
- envelope_reference/excluded/total: `1767`/`1022`/`2789`
- contract_filtered_out_ratio: `0.366440`
- class_truth_unreliable_count: `18`
- class_truth_unreliable_scored_excluded_count: `18`
- class_match_strategy_breakdown: `{'exact_qname': 107, 'none': 18}`
- match_provenance_breakdown: `{'qname_exact': 1712}`
- strict_contract_candidate_count_histogram: `{'0': 279, '1': 283, '11': 10, '12': 20, '17': 5, '18': 5, '19': 1, '2': 66, '20': 30, '28': 4, '3': 20, '35': 1, '4': 28, '48': 1, '5': 23, '6': 19, '7': 1, '79': 22, '8': 2, '9': 5}`
- core_contract_overlap: `{'reference_count': 1767, 'candidate_count': 1718, 'intersection_count': 1712, 'missing_count': 55, 'spillover_count': 6, 'avg_missing_rate': 0.08613133151349713, 'avg_spillover_rate': 0.0001117443289753045, 'avg_mutual_accuracy': 0.9137607121008827, 'weighted_missing_rate': 0.0311262026032824, 'weighted_spillover_rate': 0.003395585738539898, 'weighted_mutual_accuracy': 0.9655950366610265}`
- contract_plus_resolution_hints: `{'reference_count': 2110, 'candidate_count': 1718, 'intersection_count': 1712, 'missing_count': 398, 'spillover_count': 6, 'avg_missing_rate': 0.32459847733285235, 'avg_spillover_rate': 0.0033465826023391814, 'avg_mutual_accuracy': 0.6753132458309895, 'weighted_missing_rate': 0.18862559241706162, 'weighted_spillover_rate': 0.002843601895734597, 'weighted_mutual_accuracy': 0.8090737240075614}`
- by_language: `{'typescript': {'scored_nodes': 314, 'avg_missing_rate': 0.08613133151349713, 'avg_spillover_rate': 0.0001117443289753045, 'avg_mutual_accuracy': 0.9137607121008827, 'weighted_missing_rate': 0.0311262026032824, 'weighted_spillover_rate': 0.003395585738539898, 'weighted_mutual_accuracy': 0.9655950366610265, 'pass': False}}`

## Q2a. Reducers vs Independent Syntax Baseline

- scored_nodes: `500`
- reference/candidate/intersection: `1798`/`2714`/`1218`
- missing/spillover: `580`/`1496`
- coverage/spillover_ratio: `0.677419`/`0.832036`

## Q3. Beyond Static Contract Envelope

- scored_nodes: `314`
- avg_non_static_rate_percent: `0.96%`
- decorator_rate_percent: `0.00%`
- dynamic_dispatch_rate_percent: `0.96%`
- avg_non_static_percent_by_type: `{'dynamic_call': '0.96%'}`
- unresolved_static_target_zero: `True`
- unresolved_static_pass: `False`
- unresolved_static_avg_percent: `32.32%`
- top_unresolved_signatures: `[{'entity': 'nest.packages.core.repl.repl.repl', 'language': 'typescript', 'kind': 'function', 'file_path': 'packages/core/repl/repl.ts', 'module_qualified_name': 'nest.packages.core.repl.repl', 'unresolved_static_count': 6, 'reference_count': 2, 'unresolved_static_rate': 3.0, 'semantic_breakdown': {'member_call_unresolved': 6}}, {'entity': 'nest.packages.microservices.client.client-redis.ClientRedis.registerReadyListener', 'language': 'typescript', 'kind': 'method', 'file_path': 'packages/microservices/client/client-redis.ts', 'module_qualified_name': 'nest.packages.microservices.client.client-redis', 'unresolved_static_count': 5, 'reference_count': 2, 'unresolved_static_rate': 2.5, 'semantic_breakdown': {'member_call_unresolved': 5}}, {'entity': 'nest.packages.core.middleware.route-info-path-extractor.RouteInfoPathExtractor.constructor', 'language': 'typescript', 'kind': 'method', 'file_path': 'packages/core/middleware/route-info-path-extractor.ts', 'module_qualified_name': 'nest.packages.core.middleware.route-info-path-extractor', 'unresolved_static_count': 5, 'reference_count': 3, 'unresolved_static_rate': 1.6666666666666667, 'semantic_breakdown': {'direct_call_unresolved': 2, 'member_call_unresolved': 3}}, {'entity': 'nest.packages.platform-fastify.adapters.middie.fastify-middie.fastifyMiddie', 'language': 'typescript', 'kind': 'function', 'file_path': 'packages/platform-fastify/adapters/middie/fastify-middie.ts', 'module_qualified_name': 'nest.packages.platform-fastify.adapters.middie.fastify-middie', 'unresolved_static_count': 4, 'reference_count': 1, 'unresolved_static_rate': 4.0, 'semantic_breakdown': {'direct_call_unresolved': 1, 'member_call_unresolved': 3}}, {'entity': 'nest.packages.websockets.exceptions.base-ws-exception-filter.BaseWsExceptionFilter.catch', 'language': 'typescript', 'kind': 'method', 'file_path': 'packages/websockets/exceptions/base-ws-exception-filter.ts', 'module_qualified_name': 'nest.packages.websockets.exceptions.base-ws-exception-filter', 'unresolved_static_count': 4, 'reference_count': 1, 'unresolved_static_rate': 4.0, 'semantic_breakdown': {'member_call_unresolved': 4}}, {'entity': 'nest.packages.microservices.nest-microservice.NestMicroservice.constructor', 'language': 'typescript', 'kind': 'method', 'file_path': 'packages/microservices/nest-microservice.ts', 'module_qualified_name': 'nest.packages.microservices.nest-microservice', 'unresolved_static_count': 4, 'reference_count': 2, 'unresolved_static_rate': 2.0, 'semantic_breakdown': {'member_call_unresolved': 4}}, {'entity': 'nest.packages.websockets.socket-server-provider.SocketServerProvider.createSocketServer', 'language': 'typescript', 'kind': 'method', 'file_path': 'packages/websockets/socket-server-provider.ts', 'module_qualified_name': 'nest.packages.websockets.socket-server-provider', 'unresolved_static_count': 4, 'reference_count': 2, 'unresolved_static_rate': 2.0, 'semantic_breakdown': {'member_call_unresolved': 4}}, {'entity': 'nest.packages.core.nest-application.NestApplication.registerRouter', 'language': 'typescript', 'kind': 'method', 'file_path': 'packages/core/nest-application.ts', 'module_qualified_name': 'nest.packages.core.nest-application', 'unresolved_static_count': 4, 'reference_count': 3, 'unresolved_static_rate': 1.3333333333333333, 'semantic_breakdown': {'direct_call_unresolved': 1, 'member_call_unresolved': 3}}, {'entity': 'nest.packages.microservices.client.client-rmq.ClientRMQ.dispatchEvent', 'language': 'typescript', 'kind': 'method', 'file_path': 'packages/microservices/client/client-rmq.ts', 'module_qualified_name': 'nest.packages.microservices.client.client-rmq', 'unresolved_static_count': 4, 'reference_count': 3, 'unresolved_static_rate': 1.3333333333333333, 'semantic_breakdown': {'direct_call_unresolved': 2, 'member_call_unresolved': 2}}, {'entity': 'nest.packages.core.hooks.before-app-shutdown.hook.callBeforeAppShutdownHook', 'language': 'typescript', 'kind': 'function', 'file_path': 'packages/core/hooks/before-app-shutdown.hook.ts', 'module_qualified_name': 'nest.packages.core.hooks.before-app-shutdown.hook', 'unresolved_static_count': 4, 'reference_count': 5, 'unresolved_static_rate': 0.8, 'semantic_breakdown': {'member_call_unresolved': 4}}, {'entity': 'nest.packages.core.hooks.on-app-bootstrap.hook.callModuleBootstrapHook', 'language': 'typescript', 'kind': 'function', 'file_path': 'packages/core/hooks/on-app-bootstrap.hook.ts', 'module_qualified_name': 'nest.packages.core.hooks.on-app-bootstrap.hook', 'unresolved_static_count': 4, 'reference_count': 5, 'unresolved_static_rate': 0.8, 'semantic_breakdown': {'member_call_unresolved': 4}}, {'entity': 'nest.packages.core.hooks.on-app-shutdown.hook.callAppShutdownHook', 'language': 'typescript', 'kind': 'function', 'file_path': 'packages/core/hooks/on-app-shutdown.hook.ts', 'module_qualified_name': 'nest.packages.core.hooks.on-app-shutdown.hook', 'unresolved_static_count': 4, 'reference_count': 5, 'unresolved_static_rate': 0.8, 'semantic_breakdown': {'member_call_unresolved': 4}}, {'entity': 'nest.packages.core.hooks.on-module-destroy.hook.callModuleDestroyHook', 'language': 'typescript', 'kind': 'function', 'file_path': 'packages/core/hooks/on-module-destroy.hook.ts', 'module_qualified_name': 'nest.packages.core.hooks.on-module-destroy.hook', 'unresolved_static_count': 4, 'reference_count': 5, 'unresolved_static_rate': 0.8, 'semantic_breakdown': {'member_call_unresolved': 4}}, {'entity': 'nest.packages.core.hooks.on-module-init.hook.callModuleInitHook', 'language': 'typescript', 'kind': 'function', 'file_path': 'packages/core/hooks/on-module-init.hook.ts', 'module_qualified_name': 'nest.packages.core.hooks.on-module-init.hook', 'unresolved_static_count': 4, 'reference_count': 5, 'unresolved_static_rate': 0.8, 'semantic_breakdown': {'member_call_unresolved': 4}}, {'entity': 'nest.packages.core.injector.instance-loader.InstanceLoader.createInstancesOfInjectables', 'language': 'typescript', 'kind': 'method', 'file_path': 'packages/core/injector/instance-loader.ts', 'module_qualified_name': 'nest.packages.core.injector.instance-loader', 'unresolved_static_count': 3, 'reference_count': 1, 'unresolved_static_rate': 3.0, 'semantic_breakdown': {'member_call_unresolved': 3}}, {'entity': 'nest.packages.core.injector.instance-wrapper.InstanceWrapper.getInstanceByInquirerId', 'language': 'typescript', 'kind': 'method', 'file_path': 'packages/core/injector/instance-wrapper.ts', 'module_qualified_name': 'nest.packages.core.injector.instance-wrapper', 'unresolved_static_count': 3, 'reference_count': 1, 'unresolved_static_rate': 3.0, 'semantic_breakdown': {'member_call_unresolved': 3}}, {'entity': 'nest.packages.core.injector.module.Module.addCustomExportedProvider', 'language': 'typescript', 'kind': 'method', 'file_path': 'packages/core/injector/module.ts', 'module_qualified_name': 'nest.packages.core.injector.module', 'unresolved_static_count': 3, 'reference_count': 1, 'unresolved_static_rate': 3.0, 'semantic_breakdown': {'direct_call_unresolved': 2, 'member_call_unresolved': 1}}, {'entity': 'nest.packages.microservices.server.server-redis.ServerRedis.on', 'language': 'typescript', 'kind': 'method', 'file_path': 'packages/microservices/server/server-redis.ts', 'module_qualified_name': 'nest.packages.microservices.server.server-redis', 'unresolved_static_count': 3, 'reference_count': 1, 'unresolved_static_rate': 3.0, 'semantic_breakdown': {'direct_call_unresolved': 1, 'member_call_unresolved': 2}}, {'entity': 'nest.packages.microservices.utils.transform-pattern.utils.transformPatternToRoute', 'language': 'typescript', 'kind': 'function', 'file_path': 'packages/microservices/utils/transform-pattern.utils.ts', 'module_qualified_name': 'nest.packages.microservices.utils.transform-pattern.utils', 'unresolved_static_count': 3, 'reference_count': 1, 'unresolved_static_rate': 3.0, 'semantic_breakdown': {'direct_call_unresolved': 3}}, {'entity': 'nest.packages.core.errors.messages.UNKNOWN_DEPENDENCIES_MESSAGE', 'language': 'typescript', 'kind': 'function', 'file_path': 'packages/core/errors/messages.ts', 'module_qualified_name': 'nest.packages.core.errors.messages', 'unresolved_static_count': 3, 'reference_count': 2, 'unresolved_static_rate': 1.5, 'semantic_breakdown': {'direct_call_unresolved': 1, 'member_call_unresolved': 2}}]`

