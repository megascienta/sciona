# SCIONA Reducer Validation Report

## Run Verdict

- hard_passed: `True`
- threshold_profile: `single_language`
- strict_precision/recall/overreach: `0.979132`/`0.992494`/`0.020868`
- expanded_full_precision/recall: `0.979132`/`0.964203`
- hard_failures: `0`
- diagnostic_failures: `0`

## Mismatch Source

- independent_candidate_pressure: `210`
- core_selector_pressure: `6`
- final_edge_parity: `{'independent_overprojection': 88, 'core_missed_resolution': 0, 'core_overresolution': 128, 'normalization_contract_mismatch': 0}`
- row_dominant_cause: `{'independent_candidate_gap_dominant': 6, 'core_selector_gap_dominant': 49, 'balanced_or_none': 445}`
- top_strict_dropped_reasons: `{'no_candidates': 164, 'ambiguous_no_in_scope_candidate': 59, 'unique_without_provenance': 46, 'ambiguous_multiple_in_scope_candidates': 1}`

## Contract Boundary

- independent_static_limitation_edges: `86`
- contract_exclusion_edges: `3919`
- included_limitation_edges: `86`
- excluded_out_of_scope_edges: `3919`
- contract_leakage_rate: `0.000000`
- leakage_by_reason: `{'in_repo_unresolved': 0.0, 'dynamic': 0.0, 'relative_unresolved': 0.0}`

## Top Risks

- [high] core_analysis::method_precision_gap evidence=`{'method_precision': 0.2708333333333333}`
- [medium] core_analysis::reasoning_reliability_low evidence=`{'reasoning_structural_reliability': 0.6056338028169014}`

## Appendix

- report_schema_version: `2026-02-26`
- call_form.direct: tp=`2895`, fn=`22`, recall=`0.992458`
- call_form.member: tp=`14`, fn=`0`, recall=`1.000000`

