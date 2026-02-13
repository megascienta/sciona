# Reducer Quality Evaluation Report

Generated: 2026-02-13T20:10:33.690749+00:00
Snapshot: `30faf32da79f2e8fb1a8150907310a72ac7c31cc290f33e5495d90560bd24acb`
Sample size (`--nodes`): `500`
Runs per invocation: `10`
Calls used: `41702`
Reducers discovered via SCIONA: `20`
Languages in sample: python
DB consistency score: `1.0000`
SCIONA version: `1.0.0`
Evaluator SHA1: `c9832db782d34e31003f334c93378c848f3d1770`
Tree-sitter version: `0.20.4`
Tree-sitter-languages version: `1.10.2`
Ground truth hierarchy: direct_code > sciona_db > reducer_output

## Executive Summary

- Evaluated `20` reducers on `500` sampled entities with `41702` reducer calls.
- Overall quality snapshot: avg_determinism=`1.0000`, avg_structural_accuracy=`1.0000`, avg_identifier_overlap=`0.1687` (evidence-term overlap), avg_unknown_id_qname_rate=`0.0000`, avg_error_rate=`0.0000`.
- Secondary signal outliers: lowest evidence-term overlap=`module_call_graph_summary` (0.0); highest unknown-id/qname rate=`call_neighbors` (0.0).
- Query reducer signal: avg_empty_match_rate=`0.3163` across `2` reducers.
- Negative probe outcomes: pass_rate=`1.0000` across `2` probes.
- Determinism uniform: `1.0` across reducers.
- Secondary signals: `identifier_overlap` measures evidence-term overlap between payload identifiers and direct-code terms (not a recall metric); `unknown_id_qname_rate` penalizes only categories enabled by contract policy (out_of_scope/out_of_sample may be allowed).

## Copilot Overall Summary

Contract-aware evaluation for FastAPI is clean: all 20 reducers are schema-compliant and deterministic (1.0), with structural accuracy at 1.0 for structural reducers, zero errors, and near-total coverage (avg_coverage 0.9997). Secondary signals show low evidence-term overlap overall (avg_identifier_overlap 0.1687), including a 0.0 overlap for `module_call_graph_summary`, and query reducers show a mixed empty-match signal (`symbol_references` empty_match_rate 0.6326 vs `symbol_lookup` 0.0). Unknown-id/qname rates are 0.0 across reducers, with out_of_sample/out_of_scope proportions noted but allowed by contract policy.

Blind validation is perfect across the board: avg_blind_error_rate 0.0, id resolution 1.0, file/span validity 1.0, and all hash match metrics at 1.0 with zero diagnostics.

Contract consistency and scope checks show no mismatches: missing_required_paths, unknown_payload_keys, type_mismatches, invariant_failures, and forbidden_fields_present are all 0 for every reducer.

## Blind Summary

- avg_blind_error_rate=`0.0000`; avg_id_resolution=`1.0000`; avg_file_span_valid=`1.0000`; avg_count_consistency=`1.0000`; avg_line_span_hash_match=`1.0000`; avg_content_hash_match=`1.0000`.
- worst_blind_error_rate=`0.0`.
- hash_diagnostics_total=`0` (per-reducer cap=50).

## Blind Summary By Language

- `python`: avg_blind_error_rate=`0.0`, avg_content_hash_match=`1.0`, hash_diagnostics=`0`

## Blind Summary By Kind

- `class`: avg_blind_error_rate=`0.0`, avg_content_hash_match=`1.0`, hash_diagnostics=`0`
- `function`: avg_blind_error_rate=`0.0`, avg_content_hash_match=`1.0`, hash_diagnostics=`0`
- `method`: avg_blind_error_rate=`0.0`, avg_content_hash_match=`1.0`, hash_diagnostics=`0`
- `module`: avg_blind_error_rate=`0.0`, avg_content_hash_match=`1.0`, hash_diagnostics=`0`

## Consolidated Summary

- avg_schema_compliance=`1.0000`, avg_coverage=`0.9997`, avg_error_rate=`0.0000`.
- Full details are available in the JSON report.

## Coherence Checks

- `call_neighbors_vs_callsite_index`: expectation=`overlap`, normalization=`caller/callee ids excluding self id`, mean_jaccard_raw=`0.6`, mean_jaccard=`1.0`, pairs=`16`
- `import_targets_vs_importers_index`: expectation=`equivalent_targets`, mean_jaccard=`1.0`, pairs=`167`
- `module_file_map_vs_file_outline`: expectation=`subset`, subset_rate=`1.0`, pairs=`167`

## Sampled Entities

Population by language:
- `python`: `6363`
Population by kind:
- `class`: `660`
- `function`: `4178`
- `method`: `241`
- `module`: `1284`

## Per-Reducer Summary

Metrics key: `structural_accuracy`, `schema_compliance_score`, `coverage_score`, `determinism_score`, secondary=`identifier_overlap` (evidence-term overlap), `unknown_id_qname_rate` (out_of_scope/out_of_sample/unresolved_in_scope/resolution_failure), `omission_rate`.

- `call_neighbors`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.1068`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.0944`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`2.5868`, latency_ms_p95=`4.8598`, latency_ms_max=`6.4889`, hash_diagnostics=`0`
- `callable_overview`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.1293`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.5309`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`28.2939`, latency_ms_p95=`57.4171`, latency_ms_max=`92.1514`, hash_diagnostics=`0`
- `callable_source`: type=`projection`, structural_accuracy=`n/a`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`1.0`, unknown_id_qname_rate=`n/a` (out_of_scope=`n/a`, out_of_sample=`n/a`, unresolved_in_scope=`n/a`, resolution_failure=`n/a`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`30.296`, latency_ms_p95=`79.5752`, latency_ms_max=`102.7868`, hash_diagnostics=`0`
- `callsite_index`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.1845`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.0626`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`29.2506`, latency_ms_p95=`78.0651`, latency_ms_max=`95.5041`, hash_diagnostics=`0`
- `class_call_graph_summary`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.1`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.009`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`0.0678`, latency_ms_p95=`0.0754`, latency_ms_max=`0.2608`, hash_diagnostics=`0`
- `class_inheritance`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.1097`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.7186`, out_of_sample=`0.1018`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`24.1187`, latency_ms_p95=`72.2613`, latency_ms_max=`81.4336`, hash_diagnostics=`0`
- `class_overview`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.0027`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.4042`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`21.8471`, latency_ms_p95=`68.6554`, latency_ms_max=`76.7023`, hash_diagnostics=`0`
- `concatenated_source`: type=`aggregation`, structural_accuracy=`n/a`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`n/a`, unknown_id_qname_rate=`n/a` (out_of_scope=`n/a`, out_of_sample=`n/a`, unresolved_in_scope=`n/a`, resolution_failure=`n/a`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`13.8684`, latency_ms_p95=`48.615`, latency_ms_max=`144.8916`, hash_diagnostics=`0`
- `dependency_edges`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.1067`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.1419`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`5.3446`, latency_ms_p95=`5.708`, latency_ms_max=`10.1162`, hash_diagnostics=`0`
- `fan_summary`: type=`summary`, structural_accuracy=`n/a`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`n/a`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.0`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`2.0307`, latency_ms_p95=`4.6482`, latency_ms_max=`6.2202`, hash_diagnostics=`0`
- `file_outline`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.2544`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.3406`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`84.5058`, latency_ms_p95=`139.7078`, latency_ms_max=`241.8673`, hash_diagnostics=`0`
- `hotspot_summary`: type=`summary`, structural_accuracy=`n/a`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`n/a`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.0`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`137.4375`, latency_ms_p95=`178.2353`, latency_ms_max=`179.9927`, hash_diagnostics=`0`
- `import_targets`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.0797`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.0429`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`8.9463`, latency_ms_p95=`9.4778`, latency_ms_max=`14.9878`, hash_diagnostics=`0`
- `importers_index`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.0797`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.0744`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`9.2818`, latency_ms_p95=`9.7661`, latency_ms_max=`30.0564`, hash_diagnostics=`0`
- `module_call_graph_summary`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.0`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.0473`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`0.0763`, latency_ms_p95=`0.0925`, latency_ms_max=`0.4391`, hash_diagnostics=`0`
- `module_file_map`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.0784`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.0`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`19.8448`, latency_ms_p95=`21.7952`, latency_ms_max=`104.0494`, hash_diagnostics=`0`
- `module_overview`: type=`structural`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`0.2608`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.6672`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`7.7199`, latency_ms_p95=`13.429`, latency_ms_max=`236.4446`, hash_diagnostics=`0`
- `structural_index`: type=`summary`, structural_accuracy=`n/a`, schema_compliance_score=`1.0`, coverage_score=`1.0`, determinism_score=`1.0`, identifier_overlap=`n/a`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.0`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`159.5679`, latency_ms_p95=`208.5046`, latency_ms_max=`211.1291`, hash_diagnostics=`0`
- `symbol_lookup`: type=`query`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`0.9972`, determinism_score=`1.0`, identifier_overlap=`0.0934`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.4361`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, empty_match_rate=`0.0`, ordering_instability_rate=`0.0`, latency_ms_avg=`19.198`, latency_ms_p95=`25.9345`, latency_ms_max=`50.6213`, hash_diagnostics=`0`
- `symbol_references`: type=`query`, structural_accuracy=`1.0`, schema_compliance_score=`1.0`, coverage_score=`0.9972`, determinism_score=`1.0`, identifier_overlap=`0.1139`, unknown_id_qname_rate=`0.0` (out_of_scope=`0.0`, out_of_sample=`0.46`, unresolved_in_scope=`0.0`, resolution_failure=`0.0`), omission_rate=`0.0`, empty_match_rate=`0.6326`, ordering_instability_rate=`0.0`, latency_ms_avg=`17.8044`, latency_ms_p95=`21.0141`, latency_ms_max=`48.7786`, hash_diagnostics=`0`

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
