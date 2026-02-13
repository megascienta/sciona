# Reducer Quality Evaluation Report

Generated: 2026-02-13T20:46:53.990375+00:00
Snapshot: `8e290a83dc02daa0ecf50a80d8b2e1773fccf3ab41240af4a85bffac4ef78311`
Sample size (`--nodes`): `500`
Runs per invocation: `10`
Calls used: `41702`
Reducers discovered via SCIONA: `20`
Languages in sample: java
DB consistency score: `1.0000`
SCIONA version: `1.0.0`
Evaluator SHA1: `c9832db782d34e31003f334c93378c848f3d1770`
Tree-sitter version: `0.20.4`
Tree-sitter-languages version: `1.10.2`
Ground truth hierarchy: direct_code > sciona_db > reducer_output

## Executive Summary

- Evaluated `20` reducers on `500` sampled entities with `41702` reducer calls.
- Overall quality snapshot: avg_determinism=`1.0000`, avg_structural_accuracy=`1.0000`, avg_identifier_overlap=`0.3005` (evidence-term overlap), avg_unknown_id_qname_rate=`0.0000`, avg_error_rate=`0.0000`.
- Secondary signal outliers: lowest evidence-term overlap=`module_call_graph_summary` (0.0); highest unknown-id/qname rate=`call_neighbors` (0.0).
- Query reducer signal: avg_empty_match_rate=`0.3619` across `2` reducers.
- Negative probe outcomes: pass_rate=`1.0000` across `2` probes.
- Determinism uniform: `1.0` across reducers.
- Secondary signals: `identifier_overlap` measures evidence-term overlap between payload identifiers and direct-code terms (not a recall metric); `unknown_id_qname_rate` penalizes only categories enabled by contract policy (out_of_scope/out_of_sample may be allowed).

## Copilot Overall Summary

Contract-aware evaluation for commons-lang is clean: all 20 reducers are schema-compliant and deterministic (1.0), with structural accuracy at 1.0 for structural reducers, zero errors, and near-total coverage (avg_coverage 0.9998). Secondary signals show moderate evidence-term overlap overall (avg_identifier_overlap 0.3005), with a 0.0 overlap for `module_call_graph_summary`, and query reducers show mixed empty-match signal (`symbol_references` empty_match_rate 0.7239 vs `symbol_lookup` 0.0). Unknown-id/qname rates are 0.0 across reducers, with out_of_sample proportions present but allowed by contract policy.

Blind validation is perfect across the board: avg_blind_error_rate 0.0, id resolution 1.0, file/span validity 1.0, and all hash match metrics at 1.0 with zero diagnostics.

Contract consistency and scope checks show no mismatches: missing_required_paths, unknown_payload_keys, type_mismatches, invariant_failures, and forbidden_fields_present are all 0 for every reducer.

## Blind Summary

- avg_blind_error_rate=`0.0000`; avg_id_resolution=`1.0000`; avg_file_span_valid=`1.0000`; avg_count_consistency=`1.0000`; avg_line_span_hash_match=`1.0000`; avg_content_hash_match=`1.0000`.
- worst_blind_error_rate=`0.0`.
- hash_diagnostics_total=`0` (per-reducer cap=50).

## Blind Summary By Language

- `java`: avg_blind_error_rate=`0.0`, avg_content_hash_match=`1.0`, hash_diagnostics=`0`

## Blind Summary By Kind

- `class`: avg_blind_error_rate=`0.0`, avg_content_hash_match=`1.0`, hash_diagnostics=`0`
- `method`: avg_blind_error_rate=`0.0`, avg_content_hash_match=`1.0`, hash_diagnostics=`0`
- `module`: avg_blind_error_rate=`0.0`, avg_content_hash_match=`1.0`, hash_diagnostics=`0`

## Consolidated Summary

- avg_schema_compliance=`1.0000`, avg_coverage=`0.9998`, avg_error_rate=`0.0000`.
- Full details are available in the JSON report.

## Coherence Checks

- `call_neighbors_vs_callsite_index`: expectation=`overlap`, normalization=`caller/callee ids excluding self id`, mean_jaccard_raw=`0.6142`, mean_jaccard=`1.0`, pairs=`120`
- `import_targets_vs_importers_index`: expectation=`equivalent_targets`, mean_jaccard=`1.0`, pairs=`167`
- `module_file_map_vs_file_outline`: expectation=`subset`, subset_rate=`1.0`, pairs=`167`

## Sampled Entities

Population by language:
- `java`: `9729`
Population by kind:
- `class`: `922`
- `method`: `8273`
- `module`: `534`

## Per-Reducer Summary

Metrics key: `structural_accuracy`, `schema_compliance_score`, `coverage_score`, `determinism_score`, secondary=`identifier_overlap` (evidence-term overlap), `unknown_id_qname_rate` (out_of_scope/out_of_sample/unresolved_in_scope/resolution_failure), `omission_rate`.

- `call_neighbors`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.1954`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.6883`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`4.2678`, latency_ms_p95=`7.479`, latency_ms_max=`10.3992`, hash_diagnostics=`0`
- `callable_overview`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.1111`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.4405`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`39.7513`, latency_ms_p95=`55.2515`, latency_ms_max=`68.8961`, hash_diagnostics=`0`
- `callable_source`: type=`projection`, structural_accuracy=`n/a`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`1.0`, unknown_id_qname_rate=`n/a` (out_of_scope=`n/a`, out_of_sample=`n/a`, unresolved_in_scope=`n/a`, resolution_failure=`n/a`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`46.242`, latency_ms_p95=`64.95`, latency_ms_max=`131.4862`, hash_diagnostics=`0`
- `callsite_index`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.2879`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.3868`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`46.584`, latency_ms_p95=`63.2202`, latency_ms_max=`109.1933`, hash_diagnostics=`0`
- `class_call_graph_summary`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.0496`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.2363`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`0.1064`, latency_ms_p95=`0.1816`, latency_ms_max=`0.4936`, hash_diagnostics=`0`
- `class_inheritance`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`1.0`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.0`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`39.8458`, latency_ms_p95=`55.2754`, latency_ms_max=`69.2033`, hash_diagnostics=`0`
- `class_overview`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.0204`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.3443`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`35.1814`, latency_ms_p95=`50.127`, latency_ms_max=`57.718`, hash_diagnostics=`0`
- `concatenated_source`: type=`aggregation`, structural_accuracy=`n/a`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`n/a`, unknown_id_qname_rate=`n/a` (out_of_scope=`n/a`, out_of_sample=`n/a`, unresolved_in_scope=`n/a`, resolution_failure=`n/a`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`15.1259`, latency_ms_p95=`44.6628`, latency_ms_max=`63.0199`, hash_diagnostics=`0`
- `dependency_edges`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`1.0`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.0`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`8.2388`, latency_ms_p95=`9.136`, latency_ms_max=`11.6681`, hash_diagnostics=`0`
- `fan_summary`: type=`summary`, structural_accuracy=`n/a`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`n/a`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.0`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`3.7064`, latency_ms_p95=`7.3904`, latency_ms_max=`10.8707`, hash_diagnostics=`0`
- `file_outline`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.3306`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.5137`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`216.8053`, latency_ms_p95=`332.0657`, latency_ms_max=`476.0443`, hash_diagnostics=`0`
- `hotspot_summary`: type=`summary`, structural_accuracy=`n/a`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`n/a`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.0`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`145.4445`, latency_ms_p95=`157.3834`, latency_ms_max=`158.0608`, hash_diagnostics=`0`
- `import_targets`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.1001`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.0`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`10.8983`, latency_ms_p95=`11.676`, latency_ms_max=`38.0393`, hash_diagnostics=`0`
- `importers_index`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.1001`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.0`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`10.3007`, latency_ms_p95=`11.5151`, latency_ms_max=`14.195`, hash_diagnostics=`0`
- `module_call_graph_summary`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.0`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.2105`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`0.0897`, latency_ms_p95=`0.1654`, latency_ms_max=`2.8566`, hash_diagnostics=`0`
- `module_file_map`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.1001`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.0`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`19.5264`, latency_ms_p95=`21.4387`, latency_ms_max=`73.9608`, hash_diagnostics=`0`
- `module_overview`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.33`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.7706`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`9.2293`, latency_ms_p95=`12.7312`, latency_ms_max=`23.5798`, hash_diagnostics=`0`
- `structural_index`: type=`summary`, structural_accuracy=`n/a`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`n/a`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.0`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`156.5768`, latency_ms_p95=`168.3854`, latency_ms_max=`168.8864`, hash_diagnostics=`0`
- `symbol_lookup`: type=`query`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`0.998`, determinism_score=`1.0`, identifier_overlap=`0.0848`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.2588`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, empty_match_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`48.1106`, latency_ms_p95=`64.5847`, latency_ms_max=`103.0525`, hash_diagnostics=`0`
- `symbol_references`: type=`query`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`0.998`, determinism_score=`1.0`, identifier_overlap=`0.0974`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.3212`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, empty_match_rate=`0.7239`, ordering_instability_rate=`0.0`, latency_ms_avg=`39.9566`, latency_ms_p95=`45.5882`, latency_ms_max=`79.8545`, hash_diagnostics=`0`

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
