# SCIONA Reducer Validation Report

## Sampling

- seed: `20260219`
- requested_nodes: `500`
- sampled_nodes: `500`
- population_by_language: `{'python': 6356}`
- population_by_kind: `{'class': 658, 'function': 4178, 'method': 236, 'module': 1284}`
- sampled_by_language: `{'python': 500}`
- sampled_by_kind: `{'class': 125, 'function': 125, 'method': 125, 'module': 125}`

## Q1. Reducers vs DB Correctness

- pass: `True`
- exact_required: `True`
- reference/candidate/intersection: `499`/`499`/`499`
- missing/spillover: `0`/`0`
- mismatch_nodes: `0`

## Q2. Reducers vs Independent Within Static Contract

- pass: `False`
- target_mutual_accuracy_min: `0.990000`
- target_missing_rate_max: `0.010000`
- target_spillover_rate_max: `0.010000`
- metric_mode: `weighted_aggregate_v2`
- scored_nodes: `242`
- avg_missing_rate/avg_spillover_rate: `0.185744`/`0.009642`
- avg_mutual_accuracy: `0.808333`
- weighted_missing_rate/weighted_spillover_rate: `0.128257`/`0.024048`
- weighted_mutual_accuracy: `0.851272`
- reference/candidate/intersection: `499`/`447`/`435`
- missing/spillover: `64`/`12`
- filtering_source: `core_only`
- envelope_reference/excluded/total: `499`/`995`/`1494`
- contract_filtered_out_ratio: `0.665997`
- class_truth_unreliable_count: `0`
- class_truth_unreliable_scored_excluded_count: `0`
- class_match_strategy_breakdown: `{'exact_qname': 125}`
- match_provenance_breakdown: `{'qname_exact': 435}`
- strict_contract_candidate_count_histogram: `{'0': 376, '1': 146, '138': 2, '2': 53, '3': 30, '4': 4, '41': 1, '6': 8, '69': 12, '9': 49}`
- core_contract_overlap: `{'reference_count': 499, 'candidate_count': 447, 'intersection_count': 435, 'missing_count': 64, 'spillover_count': 12, 'avg_missing_rate': 0.18574380165289256, 'avg_spillover_rate': 0.009641873278236915, 'avg_mutual_accuracy': 0.8083333333333333, 'weighted_missing_rate': 0.1282565130260521, 'weighted_spillover_rate': 0.02404809619238477, 'weighted_mutual_accuracy': 0.8512720156555773}`
- contract_plus_resolution_hints: `{'reference_count': 690, 'candidate_count': 447, 'intersection_count': 435, 'missing_count': 255, 'spillover_count': 12, 'avg_missing_rate': 0.3934781331688548, 'avg_spillover_rate': 0.004131893307151039, 'avg_mutual_accuracy': 0.6041572783840825, 'weighted_missing_rate': 0.3695652173913043, 'weighted_spillover_rate': 0.017391304347826087, 'weighted_mutual_accuracy': 0.6196581196581197}`
- by_language: `{'python': {'scored_nodes': 242, 'avg_missing_rate': 0.18574380165289256, 'avg_spillover_rate': 0.009641873278236915, 'avg_mutual_accuracy': 0.8083333333333333, 'weighted_missing_rate': 0.1282565130260521, 'weighted_spillover_rate': 0.02404809619238477, 'weighted_mutual_accuracy': 0.8512720156555773, 'pass': False}}`

## Q2a. Reducers vs Independent Syntax Baseline

- scored_nodes: `500`
- reference/candidate/intersection: `499`/`1410`/`463`
- missing/spillover: `36`/`947`
- coverage/spillover_ratio: `0.927856`/`1.897796`

## Q3. Beyond Static Contract Envelope

- scored_nodes: `242`
- avg_non_static_rate_percent: `1.74%`
- decorator_rate_percent: `0.00%`
- dynamic_dispatch_rate_percent: `1.74%`
- avg_non_static_percent_by_type: `{'dynamic_call': '1.32%', 'dynamic_member_call': '0.41%'}`
- unresolved_static_target_zero: `True`
- unresolved_static_pass: `False`
- unresolved_static_avg_percent: `38.22%`
- top_unresolved_signatures: `[{'entity': 'fastapi.dependencies.utils._extract_form_body', 'language': 'python', 'kind': 'function', 'file_path': 'fastapi/dependencies/utils.py', 'module_qualified_name': 'fastapi.dependencies.utils', 'unresolved_static_count': 6, 'reference_count': 1, 'unresolved_static_rate': 6.0, 'semantic_breakdown': {'direct_call_unresolved': 4, 'member_call_unresolved': 2}}, {'entity': 'fastapi.tests.test_generate_unique_id_function.test_subrouter_top_level_include_overrides_generate_unique_id', 'language': 'python', 'kind': 'function', 'file_path': 'tests/test_generate_unique_id_function.py', 'module_qualified_name': 'fastapi.tests.test_generate_unique_id_function', 'unresolved_static_count': 6, 'reference_count': 3, 'unresolved_static_rate': 2.0, 'semantic_breakdown': {'member_call_unresolved': 6}}, {'entity': 'fastapi.dependencies.utils.request_body_to_args', 'language': 'python', 'kind': 'function', 'file_path': 'fastapi/dependencies/utils.py', 'module_qualified_name': 'fastapi.dependencies.utils', 'unresolved_static_count': 4, 'reference_count': 3, 'unresolved_static_rate': 1.3333333333333333, 'semantic_breakdown': {'direct_call_unresolved': 3, 'member_call_unresolved': 1}}, {'entity': 'fastapi.tests.test_generate_unique_id_function.test_app_path_operation_overrides_generate_unique_id', 'language': 'python', 'kind': 'function', 'file_path': 'tests/test_generate_unique_id_function.py', 'module_qualified_name': 'fastapi.tests.test_generate_unique_id_function', 'unresolved_static_count': 4, 'reference_count': 3, 'unresolved_static_rate': 1.3333333333333333, 'semantic_breakdown': {'member_call_unresolved': 4}}, {'entity': 'fastapi.tests.test_generate_unique_id_function.test_router_overrides_generate_unique_id', 'language': 'python', 'kind': 'function', 'file_path': 'tests/test_generate_unique_id_function.py', 'module_qualified_name': 'fastapi.tests.test_generate_unique_id_function', 'unresolved_static_count': 4, 'reference_count': 3, 'unresolved_static_rate': 1.3333333333333333, 'semantic_breakdown': {'member_call_unresolved': 4}}, {'entity': 'fastapi.tests.test_generate_unique_id_function.test_router_path_operation_overrides_generate_unique_id', 'language': 'python', 'kind': 'function', 'file_path': 'tests/test_generate_unique_id_function.py', 'module_qualified_name': 'fastapi.tests.test_generate_unique_id_function', 'unresolved_static_count': 4, 'reference_count': 3, 'unresolved_static_rate': 1.3333333333333333, 'semantic_breakdown': {'member_call_unresolved': 4}}, {'entity': 'fastapi.docs_src.websockets.tutorial003_py310.websocket_endpoint', 'language': 'python', 'kind': 'function', 'file_path': 'docs_src/websockets/tutorial003_py310.py', 'module_qualified_name': 'fastapi.docs_src.websockets.tutorial003_py310', 'unresolved_static_count': 4, 'reference_count': 4, 'unresolved_static_rate': 1.0, 'semantic_breakdown': {'member_call_unresolved': 4}}, {'entity': 'fastapi.docs_src.websockets.tutorial003_py39.websocket_endpoint', 'language': 'python', 'kind': 'function', 'file_path': 'docs_src/websockets/tutorial003_py39.py', 'module_qualified_name': 'fastapi.docs_src.websockets.tutorial003_py39', 'unresolved_static_count': 4, 'reference_count': 4, 'unresolved_static_rate': 1.0, 'semantic_breakdown': {'member_call_unresolved': 4}}, {'entity': 'fastapi.tests.test_generate_unique_id_function.test_callback_override_generate_unique_id', 'language': 'python', 'kind': 'function', 'file_path': 'tests/test_generate_unique_id_function.py', 'module_qualified_name': 'fastapi.tests.test_generate_unique_id_function', 'unresolved_static_count': 3, 'reference_count': 2, 'unresolved_static_rate': 1.5, 'semantic_breakdown': {'member_call_unresolved': 3}}, {'entity': 'fastapi.applications.FastAPI.setup', 'language': 'python', 'kind': 'method', 'file_path': 'fastapi/applications.py', 'module_qualified_name': 'fastapi.applications', 'unresolved_static_count': 3, 'reference_count': 4, 'unresolved_static_rate': 0.75, 'semantic_breakdown': {'member_call_unresolved': 3}}, {'entity': 'fastapi.routing.APIRouter.include_router', 'language': 'python', 'kind': 'method', 'file_path': 'fastapi/routing.py', 'module_qualified_name': 'fastapi.routing', 'unresolved_static_count': 3, 'reference_count': 5, 'unresolved_static_rate': 0.6, 'semantic_breakdown': {'member_call_unresolved': 3}}, {'entity': 'fastapi.routing.APIRoute.__init__', 'language': 'python', 'kind': 'method', 'file_path': 'fastapi/routing.py', 'module_qualified_name': 'fastapi.routing', 'unresolved_static_count': 3, 'reference_count': 10, 'unresolved_static_rate': 0.3, 'semantic_breakdown': {'direct_call_unresolved': 1, 'member_call_unresolved': 2}}, {'entity': 'fastapi.encoders.jsonable_encoder', 'language': 'python', 'kind': 'function', 'file_path': 'fastapi/encoders.py', 'module_qualified_name': 'fastapi.encoders', 'unresolved_static_count': 2, 'reference_count': 1, 'unresolved_static_rate': 2.0, 'semantic_breakdown': {'direct_call_unresolved': 1, 'member_call_unresolved': 1}}, {'entity': 'fastapi.security.oauth2.OAuth2.__call__', 'language': 'python', 'kind': 'method', 'file_path': 'fastapi/security/oauth2.py', 'module_qualified_name': 'fastapi.security.oauth2', 'unresolved_static_count': 2, 'reference_count': 1, 'unresolved_static_rate': 2.0, 'semantic_breakdown': {'member_call_unresolved': 2}}, {'entity': 'fastapi.security.oauth2.OAuth2AuthorizationCodeBearer.__call__', 'language': 'python', 'kind': 'method', 'file_path': 'fastapi/security/oauth2.py', 'module_qualified_name': 'fastapi.security.oauth2', 'unresolved_static_count': 2, 'reference_count': 1, 'unresolved_static_rate': 2.0, 'semantic_breakdown': {'member_call_unresolved': 2}}, {'entity': 'fastapi.security.oauth2.OAuth2PasswordBearer.__call__', 'language': 'python', 'kind': 'method', 'file_path': 'fastapi/security/oauth2.py', 'module_qualified_name': 'fastapi.security.oauth2', 'unresolved_static_count': 2, 'reference_count': 1, 'unresolved_static_rate': 2.0, 'semantic_breakdown': {'member_call_unresolved': 2}}, {'entity': 'fastapi.security.open_id_connect_url.OpenIdConnect.__call__', 'language': 'python', 'kind': 'method', 'file_path': 'fastapi/security/open_id_connect_url.py', 'module_qualified_name': 'fastapi.security.open_id_connect_url', 'unresolved_static_count': 2, 'reference_count': 1, 'unresolved_static_rate': 2.0, 'semantic_breakdown': {'member_call_unresolved': 2}}, {'entity': 'fastapi.tests.test_openapi_separate_input_output_schemas.test_create_item', 'language': 'python', 'kind': 'function', 'file_path': 'tests/test_openapi_separate_input_output_schemas.py', 'module_qualified_name': 'fastapi.tests.test_openapi_separate_input_output_schemas', 'unresolved_static_count': 2, 'reference_count': 1, 'unresolved_static_rate': 2.0, 'semantic_breakdown': {'member_call_unresolved': 2}}, {'entity': 'fastapi.docs_src.bigger_applications.app_py39.main', 'language': 'python', 'kind': 'module', 'file_path': 'docs_src/bigger_applications/app_py39/main.py', 'module_qualified_name': 'fastapi.docs_src.bigger_applications.app_py39', 'unresolved_static_count': 2, 'reference_count': 2, 'unresolved_static_rate': 1.0, 'semantic_breakdown': {'relative_import_unresolved': 2}}, {'entity': 'fastapi._compat.v2.ModelField.default', 'language': 'python', 'kind': 'method', 'file_path': 'fastapi/_compat/v2.py', 'module_qualified_name': 'fastapi._compat.v2', 'unresolved_static_count': 1, 'reference_count': 1, 'unresolved_static_rate': 1.0, 'semantic_breakdown': {'member_call_unresolved': 1}}]`

