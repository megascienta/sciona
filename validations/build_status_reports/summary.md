# SCIONA Build Status Validation Summary

This summary consolidates the JSON status reports under `validations/build_status_reports/reports/` for 10 repositories:

- `airbyte`
- `axios`
- `commons-lang`
- `fastapi`
- `guava`
- `nest`
- `pydantic`
- `sympy`
- `vscode`
- `webpack`

All numbers below come directly from `sciona status --json` `summary` payloads.

## Reporting Model

These reports should be read as a snapshot-local structural funnel plus pair/edge materialization:

- `observed_syntactic_callsites`: all syntactic call observations emitted for the committed snapshot
- `filtered_pre_persist`: observations filtered before persistence
- `persisted_callsites`: retained callsite observations inside the working set
- `callsite_pairs`: persisted `caller -> callee` candidate pairs
- `finalized_call_edges`: deduplicated finalized `node_calls` edges

Important consequence:

- `callsite_pairs` is not the same thing as `persisted_callsites`
- one retained callsite can yield more than one pair
- many persisted pairs can collapse to fewer finalized edges

## Dataset Headline

| Metric | Value |
| --- | ---: |
| Structural nodes | 291,891 |
| Structural edges | 368,329 |
| Observed syntactic callsites | 297,596 |
| Filtered before persistence | 40,409 |
| Persisted callsite observations | 257,187 |
| Persisted accepted observations | 251,493 |
| Persisted dropped observations | 5,694 |
| Persisted callsite pairs | 288,781 |
| Finalized call edges | 285,632 |

The callsite funnel closes cleanly at dataset level:

```text
observed_syntactic_callsites = filtered_pre_persist + persisted_callsites
297,596 = 40,409 + 257,187
```

Dataset ratios:

- observed-to-persisted retention: `86.42%`
- persisted acceptance inside the retained callsite working set: `97.79%`
- persisted pairs per retained callsite observation: `1.1228`
- finalized edges per persisted pair: `0.9891`

## Pre-Persist Filtering

The published reports now include populated pre-persist buckets. In this validation set, all pre-persist filtering lands in one reported class:

| Bucket | Count |
| --- | ---: |
| `unknown_out_of_scope` | 40,409 |

That means the current reports can support:

- how much was observed
- how much was filtered before persistence
- how much survived into the retained callsite working set
- how many persisted pairs and finalized edges were materialized

They do not yet distinguish multiple pre-persist out-of-scope classes inside this validation set.

## Scope Split

Persisted pair materialization by scope:

| Scope | Pairs | Share |
| --- | ---: | ---: |
| `non_tests` | 223,707 | 77.46% |
| `tests` | 65,074 | 22.54% |

Finalized call edges by scope:

| Scope | Edges | Share |
| --- | ---: | ---: |
| `non_tests` | 221,074 | 77.40% |
| `tests` | 64,558 | 22.60% |

The test/non-test split remains important in this dataset. Several repositories are strongly test-heavy in their pair surface.

## Language Summary

| Language | Observed | Filtered | Persisted | Pairs | Finalized edges | Retention | Persisted acceptance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Java | 43,954 | 1,525 | 42,429 | 43,385 | 43,345 | 96.53% | 98.46% |
| JavaScript | 3,797 | 223 | 3,574 | 3,550 | 3,534 | 94.13% | 97.65% |
| Python | 92,154 | 28,112 | 64,042 | 62,898 | 61,498 | 69.49% | 98.21% |
| TypeScript | 157,691 | 10,549 | 147,142 | 178,948 | 177,255 | 93.31% | 97.41% |

Takeaways:

- TypeScript dominates total pair and finalized-edge volume.
- Python dominates pre-persist filtering volume.
- Java has the strongest observed-to-persisted retention.
- TypeScript shows the highest pair expansion above retained callsite observations.

## Repository Highlights

### `vscode` dominates pair and edge scale

- 155,451 observed syntactic callsites
- 145,243 persisted callsite observations
- 176,856 persisted callsite pairs
- 175,171 finalized call edges

`vscode` is the main driver of TypeScript scale and of total pair expansion above retained callsite observations.

### `sympy` dominates pre-persist filtering

- 72,663 observed syntactic callsites
- 25,344 filtered before persistence
- 47,319 persisted callsite observations
- 47,109 persisted callsite pairs
- 46,558 finalized call edges

`sympy` is the strongest example of a large observed-to-persisted reduction with a stable retained surface after filtering.

### `fastapi` remains the main retained-callsite outlier

- 2,310 observed syntactic callsites
- 1,078 filtered before persistence
- 1,232 persisted callsite observations
- 716 persisted callsite pairs
- 716 finalized call edges

`fastapi` is the clearest case where the retained working set is materially smaller than the observed stream and pair materialization does not expand beyond the accepted surface.

### Test-heavy repositories are visible in the pair split

Largest test shares of persisted pairs:

| Repository | Test share |
| --- | ---: |
| `sympy` | 53.33% |
| `fastapi` | 36.73% |
| `commons-lang` | 35.87% |
| `pydantic` | 34.05% |
| `guava` | 32.98% |

## What These Reports Support

These reports support the following claims:

- SCIONA scales to large mixed-language repositories.
- The observed-to-persisted callsite funnel is measurable and stable at snapshot level.
- Persisted `callsite_pairs` materially expand beyond retained callsite observations in some repositories, especially TypeScript-heavy ones.
- Finalized call edges are very close in volume to persisted pairs, which indicates limited pair collapse after materialization at dataset level.
- Test-heavy repositories are clearly visible in the pair and edge surfaces.

These reports do not claim:

- theoretical callsite completeness
- runtime or dynamic dispatch correctness
- semantic interpretation of `unknown_out_of_scope` beyond its reported bucket identity

## Build Performance

The published reports also include build timing in each `summary` payload. The
numbers below summarize `summary.build_total_seconds` and
`summary.build_phase_timings` across the same 10 repositories.

Hardware used for these runs:

- `MacBook Pro 2019, Intel Core i9 2.4 GHz`

Dataset-level build timing:

| Metric | Value |
| --- | ---: |
| Mean total build time | `92.88 s` |
| Median total build time | `28.20 s` |
| Fastest repository | `axios` (`2.40 s`) |
| Slowest repository | `vscode` (`585.29 s`) |
| Mean build time per 1K nodes | `2.41 s` |
| Median build time per 1K nodes | `1.90 s` |

Average phase timings:

| Phase key | Mean time |
| --- | ---: |
| `compute_build_fingerprint` | `0.25 s` |
| `discover_files` | `1.10 s` |
| `prepare_snapshots` | `0.48 s` |
| `register_modules` | `0.90 s` |
| `build_structural_index` | `25.01 s` |
| `derive_call_artifacts` | `22.11 s` |
| `write_call_artifacts` | `33.17 s` |
| `rebuild_graph_index` | `1.51 s` |
| `rebuild_graph_rollups` | `1.23 s` |

Takeaways:

- `vscode` is the dominant performance outlier by total build time.
- Structural indexing, call derivation, and call artifact writing dominate the
  total build budget.
- Normalized by node volume, the dataset remains within a fairly tight range
  for most repositories even though total size varies substantially.
