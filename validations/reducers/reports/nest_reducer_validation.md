# SCIONA Reducer Validation Report

## Run Verdict

- hard_passed: `False`
- threshold_profile: `single_language`
- strict_precision/recall/overreach: `0.919612`/`0.992615`/`0.080388`
- expanded_full_precision/recall: `0.949829`/`0.861873`
- hard_failures: `1`
- diagnostic_failures: `0`
- hard_failure: basket partition violated: contract/limitation/exclusion overlap detected

## Mismatch Source

- independent_candidate_pressure: `559`
- core_selector_pressure: `16`
- final_edge_parity: `{'independent_overprojection': 186, 'core_missed_resolution': 0, 'core_overresolution': 341, 'normalization_contract_mismatch': 0}`
- row_dominant_cause: `{'independent_candidate_gap_dominant': 6, 'core_selector_gap_dominant': 89, 'balanced_or_none': 405}`
- top_strict_dropped_reasons: `{'no_candidates': 312, 'unique_without_provenance': 247, 'ambiguous_no_in_scope_candidate': 165, 'ambiguous_multiple_in_scope_candidates': 16}`

## Contract Boundary

- independent_static_limitation_edges: `308`
- contract_exclusion_edges: `732`
- included_limitation_edges: `308`
- excluded_out_of_scope_edges: `732`
- contract_leakage_rate: `0.172078`
- leakage_by_reason: `{'in_repo_unresolved': 0.1853146853146853, 'dynamic': 0.0}`

## Top Risks

- [high] core_analysis::method_precision_gap evidence=`{'method_precision': 0.7267080745341615}`
- [high] core_analysis::strict_overreach_elevated evidence=`{'strict_overreach_rate': 0.08038768529076397}`
- [medium] core_analysis::function_recall_gap evidence=`{'function_recall': 0.8780487804878049}`
- [medium] validation_workflow::strict_to_expanded_recall_drop evidence=`{'strict_recall': 0.9926153846153846, 'expanded_full_recall': 0.8618727366787378, 'delta': 0.1307426479366468}`
- [medium] core_analysis::reasoning_reliability_low evidence=`{'reasoning_structural_reliability': 0.5773584905660377}`

## Appendix

- report_schema_version: `2026-02-26`
- call_form.direct: tp=`1494`, fn=`4`, recall=`0.997330`
- call_form.member: tp=`122`, fn=`5`, recall=`0.960630`

