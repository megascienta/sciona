# Consolidated Reducer Validation Report

## Verdict Matrix

| Repo | Hard Passed | Strict P | Strict R | Overreach | Enriched R |
|---|---:|---:|---:|---:|---:|
| OpenLineage | True | 0.9394 | 0.9915 | 0.0606 | 0.8367 |
| commons_lang | True | 0.9851 | 0.9936 | 0.0149 | 0.9523 |
| fastapi | True | 0.9791 | 0.9925 | 0.0209 | 0.9642 |
| nest | False | 0.9196 | 0.9926 | 0.0804 | 0.8619 |

## Hard Failures

### nest
- basket partition violated: contract/limitation/exclusion overlap detected

## Priority Actions

### OpenLineage
- [high] core_analysis::method_precision_gap evidence={'method_precision': 0.7243243243243244}
- [high] core_analysis::strict_overreach_elevated evidence={'strict_overreach_rate': 0.06060606060606061}
- [medium] validation_workflow::strict_to_expanded_recall_drop evidence={'strict_recall': 0.9915333960489181, 'expanded_full_recall': 0.83671875, 'delta': 0.15481464604891815}

### commons_lang
- [high] core_analysis::method_recall_gap evidence={'method_recall': 0.847682119205298}
- [high] core_analysis::method_precision_gap evidence={'method_precision': 0.810126582278481}
- [medium] validation_workflow::strict_to_expanded_recall_drop evidence={'strict_recall': 0.9936305732484076, 'expanded_full_recall': 0.9522968197879859, 'delta': 0.041333753460421785}
- [medium] core_analysis::reasoning_reliability_low evidence={'reasoning_structural_reliability': 0.6896551724137931}

### fastapi
- [high] core_analysis::method_precision_gap evidence={'method_precision': 0.2708333333333333}
- [medium] core_analysis::reasoning_reliability_low evidence={'reasoning_structural_reliability': 0.6056338028169014}

### nest
- [high] core_analysis::method_precision_gap evidence={'method_precision': 0.7267080745341615}
- [high] core_analysis::strict_overreach_elevated evidence={'strict_overreach_rate': 0.08038768529076397}
- [medium] core_analysis::function_recall_gap evidence={'function_recall': 0.8780487804878049}
- [medium] validation_workflow::strict_to_expanded_recall_drop evidence={'strict_recall': 0.9926153846153846, 'expanded_full_recall': 0.8618727366787378, 'delta': 0.1307426479366468}
- [medium] core_analysis::reasoning_reliability_low evidence={'reasoning_structural_reliability': 0.5773584905660377}
