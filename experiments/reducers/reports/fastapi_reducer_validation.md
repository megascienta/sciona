# SCIONA Reducer Validation Report

## Executive Summary

- repo=fastapi
- sampled_nodes=500
- invariants_passed=True
- interpretation_note: independent truth is a deterministic static proxy, not absolute ground truth.

## Run Verdict

- passed: `True`
- hard_passed: `True`
- threshold_profile: `single_language`
- gate_reducer_db_exact: `True`
- gate_aligned_scoring: `True`
- gate_parse_coverage: `True`
- gate_contract_truth_pure: `True`
- gate_contract_truth_resolved: `True`
- gate_parser_deterministic: `True`
- gate_no_duplicate_contract_edges: `True`
- gate_typescript_relative_index_contract: `True`
- gate_class_truth_nonempty_rate: `True`
- gate_class_truth_match_rate: `True`
- gate_scoped_call_normalization: `True`
- gate_contract_recall_min: `True`
- gate_overreach_rate_max: `True`
- gate_member_call_recall_min: `False`
- gate_equal_contract_metrics_when_exact: `True`
- diagnostic_failure: member-call recall quality gate failed

## Internal Integrity (Hard Gates)

- valid: `True`
- static_projection_precision: `1.000000`
- static_projection_recall: `1.000000`
- parser_stability_score: `1.000000`

## Contract Alignment (Strict Proxy)

- static_contract_precision: `0.964262`
- static_contract_recall: `0.979167`
- static_overreach_rate: `0.035738`
- static_divergence_index: `0.055123`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.7883211678832117, 0.984553560215999], 'recall_ci95': [0.8829787234042553, 0.9881074899942824], 'n': 500}, 'method': {'precision_ci95': [0.125, 0.36764705882352944], 'recall_ci95': [0.45454545454545453, 0.8666666666666667], 'n': 125}}`

## Expanded Proxy Alignment (Diagnostic)

- reducer_vs_enriched_truth_precision: `0.964262`
- reducer_vs_enriched_truth_recall: `0.961716`
- db_vs_enriched_truth_precision: `0.964262`
- db_vs_enriched_truth_recall: `0.961716`
- reducer_vs_enriched_truth_divergence_index: `0.071383`
- inclusion_policy: `{'base': 'contract_truth_edges + limitation_edges', 'scope_exclusions': ['standard_call', 'external'], 'limitation_focus': ['dynamic', 'in_repo_unresolved', 'relative_unresolved'], 'confidence_tiers': {'high': ['in_repo_unresolved'], 'low': ['dynamic', 'relative_unresolved']}, 'notes': 'Expanded truth is diagnostic-only and non-gating.'}`
- tier.high_conf: reducer_p/r=`0.964262`/`0.964262`, db_p/r=`0.964262`/`0.964262`, divergence=`0.069010`
- tier.full: reducer_p/r=`0.964262`/`0.961716`, db_p/r=`0.964262`/`0.961716`, divergence=`0.071383`
- tier_edge_counts: `{'high_conf_edges': 3022, 'full_edges': 3030}`
- scope_split_counts: `{'excluded_out_of_scope_edges': 4722, 'included_limitation_edges': 62, 'excluded_out_of_scope_by_reason': {'standard_call': 34, 'external': 4688}, 'included_limitation_by_reason': {'in_repo_unresolved': 48, 'dynamic': 8, 'relative_unresolved': 6}}`
Reason-level expanded proxy recall:
- reason.dynamic: reducer_recall=`0.000000`, db_recall=`0.000000`, reducer_tp/fn=`0/4`
- reason.in_repo_unresolved: reducer_recall=`0.000000`, db_recall=`0.000000`, reducer_tp/fn=`0/46`
- reason.relative_unresolved: reducer_recall=`0.000000`, db_recall=`0.000000`, reducer_tp/fn=`0/4`
- uncertainty_intervals: `{'micro': {'precision_ci95': [0.7862318840579711, 0.9845171588188348], 'recall_ci95': [0.8017699115044248, 0.9800741427247451], 'n': 500}}`

## Prompt Reliability (Heuristic Diagnostics)

- navigation_structural_reliability: `0.989504`
- reasoning_structural_reliability: `0.358067`
- coupling_stability_index: `0.964262`
- prompt_reliability_version: `v1`
- weights: `{'navigation': {'fp_weight': 1.0, 'fn_weight': 1.0}, 'reasoning': {'fp_weight': 1.0, 'fn_weight': 1.2}}`
- component_contributions: `{'navigation': {'tp': 2734, 'fp': 6, 'fn': 23, 'penalty_fp': 6.0, 'penalty_fn': 23.0, 'denominator': 2763.0}, 'reasoning': {'tp': 83, 'fp': 102, 'fn': 39, 'penalty_fp': 102.0, 'penalty_fn': 46.8, 'denominator': 231.8}}`
- enrichment_noise_ratio: `0.017822`

## Language Breakdown

- python: sampled_nodes=`500`, population_nodes=`6363`, projection_p/r=`1.000000`/`1.000000`, contract_p/r=`0.964262`/`0.979167`, expanded_p/r=`0.964262`/`0.961716`, contract_overreach=`0.035738`, projection_tp/fp/fn=`3022/0/0`, contract_tp/fp/fn=`2914/108/62`
- python:module: recall=`0.991658`, precision=`0.997810`, tp/fp/fn=`2734/6/23`
- python:class: recall=`1.000000`, precision=`1.000000`, tp/fp/fn=`97/0/0`
- python:function: recall=`0.676768`, precision=`0.572650`, tp/fp/fn=`67/50/32`
- python:method: recall=`0.695652`, precision=`0.235294`, tp/fp/fn=`16/52/7`

Expanded Proxy Alignment by language:kind
- python:module: strict_p/r=`0.997810`/`0.991658`, expanded_p/r=`0.997810`/`0.989862`
- python:class: strict_p/r=`1.000000`/`1.000000`, expanded_p/r=`1.000000`/`1.000000`
- python:function: strict_p/r=`0.572650`/`0.676768`, expanded_p/r=`0.572650`/`0.485507`
- python:method: strict_p/r=`0.235294`/`0.695652`, expanded_p/r=`0.235294`/`0.484848`

Strict vs Expanded delta by kind (top-5 worst recall delta)
- python:method: delta_recall=`0.210804`, delta_precision=`0.000000`
- python:function: delta_recall=`0.191260`, delta_precision=`0.000000`
- python:module: delta_recall=`0.001795`, delta_precision=`0.000000`
- python:class: delta_recall=`0.000000`, delta_precision=`0.000000`

## Call Resolution Diagnostics

- call_form.direct: tp=`2896`, fn=`41`, recall=`0.986040`
- call_form.member: tp=`18`, fn=`21`, recall=`0.461538`
- mismatch_attribution.core_missed_resolution: `0`
- mismatch_attribution.core_overresolution: `172`
- mismatch_attribution.normalization_contract_mismatch: `0`
- mismatch_attribution.independent_overprojection: `126`

## Out-of-Contract Distribution

- call: `55`
- import: `7`

Breakdown by `edge_type::language::reason`:
- call::python::dynamic: `8`
- call::python::in_repo_unresolved: `47`
- import::python::in_repo_unresolved: `1`
- import::python::relative_unresolved: `6`

Note: `enrichment_edges` includes only in-repo out-of-contract edges (unresolved, dynamic, standard-call filtered); external edges are excluded.

## Independent Parser Coverage & Totals

- coverage.python: files_parsed/files_total=`1284/1284` (1.000000)
- raw_call_edges: `15400`
- raw_import_edges: `4856`
- normalized_call_edges: `15400`
- normalized_import_edges: `4856`
- contract_truth_edges: `2976`
- enrichment_edges: `54`
- enriched_truth_edges: `3030`
- expanded_high_conf_edges: `3022`
- expanded_full_edges: `3030`
- excluded_out_of_scope_edges: `4722`
- included_limitation_edges: `62`

## Core Metrics

- static_contract_recall: `0.979167`
- static_overreach_rate: `0.035738`
- overreach_count: `108`
- reducer_edge_total: `3022`

## Action Priority Board

- [high] core_analysis::method_recall_gap evidence=`{'method_recall': 0.6956521739130435}`
- [high] core_analysis::method_precision_gap evidence=`{'method_precision': 0.23529411764705882}`
- [medium] core_analysis::function_recall_gap evidence=`{'function_recall': 0.6767676767676768}`
- [medium] core_analysis::reasoning_reliability_low evidence=`{'reasoning_structural_reliability': 0.35806729939603105}`

## Metric Definitions & Schema

- report_schema_version: `2026-02-23`
- enriched_alignment_precision: layer=`enrichment_practical`, source=`reducer_vs_enriched_truth`, formula=`tp / (tp + fp)`
- enriched_alignment_recall: layer=`enrichment_practical`, source=`reducer_vs_enriched_truth`, formula=`tp / (tp + fn)`
- expanded_full_precision: layer=`enrichment_practical`, source=`reducer_vs_expanded_full`, formula=`tp / (tp + fp)`
- expanded_full_recall: layer=`enrichment_practical`, source=`reducer_vs_expanded_full`, formula=`tp / (tp + fn)`
- expanded_high_conf_precision: layer=`enrichment_practical`, source=`reducer_vs_expanded_high_conf`, formula=`tp / (tp + fp)`
- expanded_high_conf_recall: layer=`enrichment_practical`, source=`reducer_vs_expanded_high_conf`, formula=`tp / (tp + fn)`
- static_contract_precision: layer=`static_contract_alignment`, source=`reducer_vs_contract_truth`, formula=`tp / (tp + fp)`
- static_contract_recall: layer=`static_contract_alignment`, source=`reducer_vs_contract_truth`, formula=`tp / (tp + fn)`
- static_overreach_rate: layer=`static_contract_alignment`, source=`reducer_vs_contract_truth`, formula=`fp / (tp + fp)`
- static_projection_precision: layer=`internal_integrity`, source=`reducer_vs_db`, formula=`tp / (tp + fp)`
- static_projection_recall: layer=`internal_integrity`, source=`reducer_vs_db`, formula=`tp / (tp + fn)`

