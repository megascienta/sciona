# Consolidated Reducer Validation Report

Date: 2026-02-22  
Scope: regenerated reports in `experiments/reducers/reports/` for:
- Apache Commons Lang (Java)
- FastAPI (Python)
- Nest (TypeScript)

## Method

Validation compares three views for sampled nodes (`N=500` per repository):
1. reducer output
2. direct DB edges
3. independent parser contract truth

Only in-repo contract-compatible edges are scored. Run acceptance is gated by hard invariants and threshold quality gates.

## Current Results

| Repository | Language | Invariants | Contract Recall | Overreach Rate | Member Recall | Class Truth Nonempty | Class Truth Match |
| ---------- | -------- | ---------- | --------------- | -------------- | ------------- | -------------------- | ----------------- |
| Apache Commons Lang | Java | **True** | **0.9904** | **0.0155** | n/a | **1.0000** | **1.0000** |
| FastAPI | Python | **True** | **0.9723** | **0.0023** | **0.8548** | **1.0000** | **1.0000** |
| Nest | TypeScript | **True** | **0.9776** | **0.0530** | **0.8927** | **1.0000** | **1.0000** |

Notes:
- Java `member_call_recall` is not applicable in this sample (`gate_member_call_recall_min = n/a`), not a failure.
- All repositories pass `gate_reducer_db_exact` and `gate_equal_contract_metrics_when_exact`.
- All repositories pass class-truth quality gates (`nonempty` and `match-rate`).

## Taxonomy Snapshot

Validation outputs are now split into:
1. `static_structural_validity`
2. `semantic_alignment`
3. `prompt_fitness`

High-level values from current reports:

| Repository | Semantic Divergence Index | Navigation Reliability | Reasoning Reliability |
| ---------- | ------------------------- | ---------------------- | --------------------- |
| Apache Commons Lang | **0.0248** | **0.8475** | **0.6571** |
| FastAPI | **0.0299** | **0.9873** | **0.7537** |
| Nest | **0.0731** | **0.9980** | **0.7252** |

Interpretation:
- Navigation-oriented prompt fitness is strongest for Nest and FastAPI.
- Reasoning-oriented prompt fitness remains the tighter bottleneck across all three repos.

## Baseline Comparison

Baseline commit: `ee0a2e2`.

| Repository | Recall (Old -> New) | Overreach (Old -> New) | Invariants (Old -> New) |
| ---------- | ------------------- | ---------------------- | ----------------------- |
| Apache Commons Lang | `0.7937 -> 0.9904` | `0.0166 -> 0.0155` | `True -> True` |
| FastAPI | `0.9783 -> 0.9723` | `0.0167 -> 0.0023` | `True -> True` |
| Nest | `0.9442 -> 0.9776` | `0.0843 -> 0.0530` | `True -> True` |

## Diagnostic Attribution Snapshot

Report payloads include `mismatch_attribution_breakdown` and per-node `mismatch_attribution`. These are diagnostic aids for triage and are secondary to run-gating metrics.

Current attribution totals:

| Repository | independent_overprojection | core_overresolution | core_missed_resolution | normalization_contract_mismatch |
| ---------- | -------------------------- | ------------------- | ---------------------- | ------------------------------- |
| Apache Commons Lang | 1210 | 1242 | 0 | 0 |
| FastAPI | 94 | 19 | 0 | 0 |
| Nest | 67 | 125 | 0 | 0 |

Interpretation guidance:
- Use attribution totals to identify where to investigate (`per_node` details), not as acceptance criteria.
- Acceptance is determined by invariants and core metrics.

## Verdict

Validation workflow is currently in a good state across Java/Python/TypeScript benchmark repositories:
- all hard gates pass on all three repositories;
- reducer-to-DB consistency remains exact where required;
- contract recall is high with controlled overreach;
- class matching quality gates remain stable after Java class-truth hardening.
