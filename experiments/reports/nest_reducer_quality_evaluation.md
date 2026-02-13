# Reducer Quality Evaluation Report

Generated: 2026-02-13T20:22:21.230935+00:00
Snapshot: `d6351afe8510b9c36f3eb6d444f7beec4bc4c88fccb9de3808fd3913372ee523`
Sample size (`--nodes`): `500`
Runs per invocation: `10`
Calls used: `41702`
Reducers discovered via SCIONA: `20`
Languages in sample: typescript
DB consistency score: `1.0000`
SCIONA version: `1.0.0`
Evaluator SHA1: `c9832db782d34e31003f334c93378c848f3d1770`
Tree-sitter version: `0.20.4`
Tree-sitter-languages version: `1.10.2`
Ground truth hierarchy: direct_code > sciona_db > reducer_output

## Executive Summary

- Evaluated `20` reducers on `500` sampled entities with `41702` reducer calls.
- Overall quality snapshot: avg_determinism=`1.0000`, avg_structural_accuracy=`1.0000`, avg_identifier_overlap=`0.2042` (evidence-term overlap), avg_unknown_id_qname_rate=`0.0000`, avg_error_rate=`0.0000`.
- Secondary signal outliers: lowest evidence-term overlap=`module_call_graph_summary` (0.0); highest unknown-id/qname rate=`call_neighbors` (0.0).
- Query reducer signal: avg_empty_match_rate=`0.2997` across `2` reducers.
- Negative probe outcomes: pass_rate=`1.0000` across `2` probes.
- Determinism uniform: `1.0` across reducers.
- Secondary signals: `identifier_overlap` measures evidence-term overlap between payload identifiers and direct-code terms (not a recall metric); `unknown_id_qname_rate` penalizes only categories enabled by contract policy (out_of_scope/out_of_sample may be allowed).

## Copilot Overall Summary

Contract-aware evaluation for Nest is clean: all 20 reducers are schema-compliant and deterministic (1.0), with structural accuracy at 1.0 for structural reducers, zero errors, and near-total coverage (avg_coverage 0.9997). Secondary signals show modest evidence-term overlap overall (avg_identifier_overlap 0.2042), with a 0.0 overlap for `module_call_graph_summary`, and query reducers show mixed empty-match signal (`symbol_references` empty_match_rate 0.5994 vs `symbol_lookup` 0.0). Unknown-id/qname rates are 0.0 across reducers, with out_of_sample proportions present but allowed by contract policy.

Blind validation is perfect across the board: avg_blind_error_rate 0.0, id resolution 1.0, file/span validity 1.0, and all hash match metrics at 1.0 with zero diagnostics.

Contract consistency and scope checks show no mismatches: missing_required_paths, unknown_payload_keys, type_mismatches, invariant_failures, and forbidden_fields_present are all 0 for every reducer.

## Blind Summary

- avg_blind_error_rate=`0.0000`; avg_id_resolution=`1.0000`; avg_file_span_valid=`1.0000`; avg_count_consistency=`1.0000`; avg_line_span_hash_match=`1.0000`; avg_content_hash_match=`1.0000`.
- worst_blind_error_rate=`0.0`.
- hash_diagnostics_total=`0` (per-reducer cap=50).

## Blind Summary By Language

- `typescript`: avg_blind_error_rate=`0.0`, avg_content_hash_match=`1.0`, hash_diagnostics=`0`

## Blind Summary By Kind

- `class`: avg_blind_error_rate=`0.0`, avg_content_hash_match=`1.0`, hash_diagnostics=`0`
- `function`: avg_blind_error_rate=`0.0`, avg_content_hash_match=`1.0`, hash_diagnostics=`0`
- `method`: avg_blind_error_rate=`0.0`, avg_content_hash_match=`1.0`, hash_diagnostics=`0`
- `module`: avg_blind_error_rate=`0.0`, avg_content_hash_match=`1.0`, hash_diagnostics=`0`

## Consolidated Summary

- avg_schema_compliance=`1.0000`, avg_coverage=`0.9997`, avg_error_rate=`0.0000`.
- Full details are available in the JSON report.

## Coherence Checks

- `call_neighbors_vs_callsite_index`: expectation=`overlap`, normalization=`caller/callee ids excluding self id`, mean_jaccard_raw=`0.615`, mean_jaccard=`1.0`, pairs=`71`
- `import_targets_vs_importers_index`: expectation=`equivalent_targets`, mean_jaccard=`1.0`, pairs=`167`
- `module_file_map_vs_file_outline`: expectation=`subset`, subset_rate=`1.0`, pairs=`167`

## Sampled Entities

Population by language:
- `typescript`: `5918`
Population by kind:
- `class`: `1337`
- `function`: `206`
- `method`: `2716`
- `module`: `1659`

## Per-Reducer Summary

Metrics key: `structural_accuracy`, `schema_compliance_score`, `coverage_score`, `determinism_score`, secondary=`identifier_overlap` (evidence-term overlap), `unknown_id_qname_rate` (out_of_scope/out_of_sample/unresolved_in_scope/resolution_failure), `omission_rate`.

- `call_neighbors`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.146`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.4186`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`2.4808`, latency_ms_p95=`4.1922`, latency_ms_max=`9.6143`, hash_diagnostics=`0`
- `callable_overview`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.1533`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.5361`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`23.0888`, latency_ms_p95=`34.6081`, latency_ms_max=`44.5554`, hash_diagnostics=`0`
- `callable_source`: type=`projection`, structural_accuracy=`n/a`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`1.0`, unknown_id_qname_rate=`n/a` (out_of_scope=`n/a`, out_of_sample=`n/a`, unresolved_in_scope=`n/a`, resolution_failure=`n/a`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`23.5186`, latency_ms_p95=`35.6866`, latency_ms_max=`41.0557`, hash_diagnostics=`0`
- `callsite_index`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.2421`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.2643`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`22.4526`, latency_ms_p95=`34.191`, latency_ms_max=`42.2079`, hash_diagnostics=`0`
- `class_call_graph_summary`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.0433`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.0745`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`0.0682`, latency_ms_p95=`0.1221`, latency_ms_max=`0.3284`, hash_diagnostics=`0`
- `class_inheritance`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`1.0`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.0`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`22.4321`, latency_ms_p95=`34.8206`, latency_ms_max=`44.0296`, hash_diagnostics=`0`
- `class_overview`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.0149`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.4611`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`20.2727`, latency_ms_p95=`32.5018`, latency_ms_max=`37.8534`, hash_diagnostics=`0`
- `concatenated_source`: type=`aggregation`, structural_accuracy=`n/a`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`n/a`, unknown_id_qname_rate=`n/a` (out_of_scope=`n/a`, out_of_sample=`n/a`, unresolved_in_scope=`n/a`, resolution_failure=`n/a`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`14.0594`, latency_ms_p95=`29.184`, latency_ms_max=`59.9304`, hash_diagnostics=`0`
- `dependency_edges`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.0622`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.3178`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`5.1798`, latency_ms_p95=`5.7629`, latency_ms_max=`6.9187`, hash_diagnostics=`0`
- `fan_summary`: type=`summary`, structural_accuracy=`n/a`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`n/a`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.0`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`2.3791`, latency_ms_p95=`4.3818`, latency_ms_max=`5.7923`, hash_diagnostics=`0`
- `file_outline`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.1437`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.2791`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`67.2737`, latency_ms_p95=`82.5026`, latency_ms_max=`97.8806`, hash_diagnostics=`0`
- `hotspot_summary`: type=`summary`, structural_accuracy=`n/a`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`n/a`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.0`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`112.8228`, latency_ms_p95=`124.53`, latency_ms_max=`131.124`, hash_diagnostics=`0`
- `import_targets`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.0471`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.1919`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`5.8407`, latency_ms_p95=`6.4463`, latency_ms_max=`9.1087`, hash_diagnostics=`0`
- `importers_index`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.0471`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.3164`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`5.8659`, latency_ms_p95=`6.1787`, latency_ms_max=`11.98`, hash_diagnostics=`0`
- `module_call_graph_summary`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.0`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.0695`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`0.0545`, latency_ms_p95=`0.1009`, latency_ms_max=`0.3013`, hash_diagnostics=`0`
- `module_file_map`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.0429`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.0`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`12.9289`, latency_ms_p95=`15.1567`, latency_ms_max=`31.3213`, hash_diagnostics=`0`
- `module_overview`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.1393`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.4186`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`3.0021`, latency_ms_p95=`3.9704`, latency_ms_max=`6.0666`, hash_diagnostics=`0`
- `structural_index`: type=`summary`, structural_accuracy=`n/a`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`n/a`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.0`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`126.2699`, latency_ms_p95=`129.3933`, latency_ms_max=`130.6802`, hash_diagnostics=`0`
- `symbol_lookup`: type=`query`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`0.9969`, determinism_score=`1.0`, identifier_overlap=`0.0779`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.4293`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, empty_match_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`19.136`, latency_ms_p95=`22.9314`, latency_ms_max=`59.8205`, hash_diagnostics=`0`
- `symbol_references`: type=`query`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`0.9969`, determinism_score=`1.0`, identifier_overlap=`0.1076`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.5075`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, empty_match_rate=`0.5994`, ordering_instability_rate=`0.0`, latency_ms_avg=`24.9721`, latency_ms_p95=`29.0259`, latency_ms_max=`49.732`, hash_diagnostics=`0`

## Contract Consistency

- `call_neighbors`: missing_required_paths=`0`, unknown_payload_keys=`0`, type_mismatches=`0`, invariant_failures=`0`, forbidden_fields_present=`0`
- `callable_overview`: missing_required_paths=`0`, unknown_payload_keys=`0`, type_mismatches=`0`, invariant_failures=`0`, forbidden_fields_present=`0`
- `callable_source`: missing_required_paths=`0`, unknown_payload_keys=`0`, type_mismatches=`0`, invariant_failures=`0`, forbidden_fields_present=`0`
- `callsite_index`: missing_required_paths=`0`, unknown_payload_keys=`0`, type_mismatches=`0`, invariant_failures=`0`, forbidden_fields_present=`0`
- `class_call_graph_summary`: missing_required_paths=`0`, unknown_payload_keys=`0`, type_mismatches=`0`, invariant_failures=`0`, forbidden_fields_present=`0`
- `class_inheritance`: missing_required_paths=`0`, unknown_payload_keys=`0`, type_mismatches=`0`, invariant_failures=`0`, forbidden_fields_present=`0`
- `class_overview`: missing_required_paths=`0`, unknown_payload_keys=`0`, type_mismatches=`0`, invariant_failures=`0`, forbidden_fields_present=`0`
- `concatenated_source`: missing_required_paths=`0`, unknown_payload_keys=`0`, type_mismatches=`0`, invariant_failures=`0`, forbidden_fields_present=`0`
- `dependency_edges`: missing_required_paths=`0`, unknown_payload_keys=`0`, type_mismatches=`0`, invariant_failures=`0`, forbidden_fields_present=`0`
- `fan_summary`: missing_required_paths=`0`, unknown_payload_keys=`0`, type_mismatches=`0`, invariant_failures=`0`, forbidden_fields_present=`0`
- `file_outline`: missing_required_paths=`0`, unknown_payload_keys=`0`, type_mismatches=`0`, invariant_failures=`0`, forbidden_fields_present=`0`
- `hotspot_summary`: missing_required_paths=`0`, unknown_payload_keys=`0`, type_mismatches=`0`, invariant_failures=`0`, forbidden_fields_present=`0`
- `import_targets`: missing_required_paths=`0`, unknown_payload_keys=`0`, type_mismatches=`0`, invariant_failures=`0`, forbidden_fields_present=`0`
- `importers_index`: missing_required_paths=`0`, unknown_payload_keys=`0`, type_mismatches=`0`, invariant_failures=`0`, forbidden_fields_present=`0`
- `module_call_graph_summary`: missing_required_paths=`0`, unknown_payload_keys=`0`, type_mismatches=`0`, invariant_failures=`0`, forbidden_fields_present=`0`
- `module_file_map`: missing_required_paths=`0`, unknown_payload_keys=`0`, type_mismatches=`0`, invariant_failures=`0`, forbidden_fields_present=`0`
- `module_overview`: missing_required_paths=`0`, unknown_payload_keys=`0`, type_mismatches=`0`, invariant_failures=`0`, forbidden_fields_present=`0`
- `structural_index`: missing_required_paths=`0`, unknown_payload_keys=`0`, type_mismatches=`0`, invariant_failures=`0`, forbidden_fields_present=`0`
- `symbol_lookup`: missing_required_paths=`0`, unknown_payload_keys=`0`, type_mismatches=`0`, invariant_failures=`0`, forbidden_fields_present=`0`
- `symbol_references`: missing_required_paths=`0`, unknown_payload_keys=`0`, type_mismatches=`0`, invariant_failures=`0`, forbidden_fields_present=`0`
