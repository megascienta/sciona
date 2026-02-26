# SCIONA Reducer Validation Report

## Run Verdict

- hard_passed: `True`
- threshold_profile: `single_language`
- strict_precision/recall/overreach: `0.985129`/`0.993631`/`0.014871`
- enriched_full_precision/recall: `0.988185`/`0.952297`
- hard_failures: `0`
- diagnostic_failures: `1`
- diagnostic_failure: kind precision floor gate failed

## Mismatch Source

- independent_candidate_pressure: `6623`
- core_selector_pressure: `134`
- final_edge_parity: `{'independent_overprojection': 295, 'core_missed_resolution': 0, 'core_overresolution': 337, 'normalization_contract_mismatch': 0}`
- row_dominant_cause: `{'independent_candidate_gap_dominant': 23, 'core_selector_gap_dominant': 66, 'balanced_or_none': 411}`
- top_strict_dropped_reasons: `{'no_candidates': 3404, 'unique_without_provenance': 3219, 'ambiguous_no_in_scope_candidate': 229, 'ambiguous_multiple_in_scope_candidates': 46}`

## Contract Boundary

- independent_static_limitation_edges: `227`
- contract_exclusion_edges: `1716`
- included_limitation_edges: `227`
- excluded_out_of_scope_edges: `1716`
- contract_leakage_rate: `0.066079`
- leakage_by_reason: `{'in_repo_unresolved': 0.06607929515418502}`

## Top Risks

- [high] core_analysis::method_recall_gap confidence=`high` evidence=`{'method_recall': 0.847682119205298}`
- [high] core_analysis::method_precision_gap confidence=`high` evidence=`{'method_precision': 0.810126582278481}`
- [medium] validation_workflow::strict_to_expanded_recall_drop confidence=`medium` evidence=`{'strict_recall': 0.9936305732484076, 'expanded_full_recall': 0.9522968197879859, 'delta': 0.041333753460421785}`
- [medium] core_analysis::reasoning_reliability_low confidence=`medium` evidence=`{'reasoning_structural_reliability': 0.6896551724137931}`

## Appendix

- report_schema_version: `2026-02-26`
- call_form.direct: tp=`4836`, fn=`31`, recall=`0.993631`
- call_form.member: tp=`0`, fn=`0`, recall=`None`

