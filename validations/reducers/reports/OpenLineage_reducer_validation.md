# SCIONA Reducer Validation Report

## Run Verdict

- hard_passed: `True`
- threshold_profile: `multi_language`
- strict_precision/recall/overreach: `0.939394`/`0.991533`/`0.060606`
- enriched_full_precision/recall: `0.954545`/`0.836719`
- hard_failures: `0`
- diagnostic_failures: `0`

## Mismatch Source

- independent_candidate_pressure: `1302`
- core_selector_pressure: `297`
- final_edge_parity: `{'independent_overprojection': 19, 'core_missed_resolution': 0, 'core_overresolution': 80, 'normalization_contract_mismatch': 0}`
- row_dominant_cause: `{'independent_candidate_gap_dominant': 6, 'core_selector_gap_dominant': 40, 'balanced_or_none': 454}`
- top_strict_dropped_reasons: `{'no_candidates': 1086, 'unique_without_provenance': 216, 'ambiguous_no_in_scope_candidate': 162, 'ambiguous_multiple_in_scope_candidates': 9}`

## Contract Boundary

- independent_static_limitation_edges: `217`
- contract_exclusion_edges: `3057`
- included_limitation_edges: `217`
- excluded_out_of_scope_edges: `3057`
- contract_leakage_rate: `0.078341`
- leakage_by_reason: `{'in_repo_unresolved': 0.07834101382488479}`

## Top Risks

- [high] core_analysis::method_precision_gap confidence=`high` evidence=`{'method_precision': 0.7243243243243244}`
- [high] core_analysis::strict_overreach_elevated confidence=`high` evidence=`{'strict_overreach_rate': 0.06060606060606061}`
- [medium] validation_workflow::strict_to_expanded_recall_drop confidence=`medium` evidence=`{'strict_recall': 0.9915333960489181, 'expanded_full_recall': 0.83671875, 'delta': 0.15481464604891815}`

## Appendix

- report_schema_version: `2026-02-26`
- call_form.direct: tp=`966`, fn=`4`, recall=`0.995876`
- call_form.member: tp=`89`, fn=`4`, recall=`0.956989`

