# SCIONA Build Status Validation Summary

This summary consolidates the JSON status reports under `validations/build_status_reports/reports/`, generated on **2026-03-12** for 10 repositories:

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

All numbers below are taken from `sciona status --json` `summary` payloads.

## Reporting Semantics

The reports should now be read as a snapshot-local funnel, not as a claim of theoretical completeness.

- `observed_syntactic_callsites`: raw syntactic callsites observed for the committed snapshot
- `filtered_pre_persist`: observed callsites excluded before `call_sites` persistence
- `persisted_callsites`: the filtered artifact working set used by reporting and final call derivation
- `persisted_accepted` / `persisted_dropped`: final outcomes inside that persisted working set
- `drop_classification`: closed reporting buckets over persisted dropped rows
- `filtered_pre_persist_buckets`: pre-persist reason buckets when available

Important boundary:

- These reports support statements about the observed-to-persisted funnel and persisted drop mix.
- They do not support claims like "all theoretical callsites are covered" or "all filtered rows are external" unless the relevant bucket data is populated.

## Headline Funnel

| Metric | Value |
| --- | ---: |
| Indexed files | 27,700 |
| Discovered files | 27,711 |
| Structural nodes | 291,891 |
| Structural edges | 368,329 |
| Observed syntactic callsites | 297,596 |
| Filtered before persistence | 40,409 |
| Persisted `call_sites` | 257,187 |
| Persisted accepted | 251,493 |
| Persisted dropped | 5,694 |
| Persisted acceptance rate | 97.79% |
| Observed-to-persisted retention | 86.42% |

The primary conservation identity holds at dataset level:

```text
observed_syntactic_callsites = filtered_pre_persist + persisted_callsites
297,596 = 40,409 + 257,187
```

## Persisted Drop Classification

The persisted dropped working set falls into explicit reporting buckets. Across the 5,694 persisted dropped rows:

| Bucket | Count | Share of persisted drops |
| --- | ---: | ---: |
| `ambiguous_in_scope` | 3,263 | 57.3% |
| `insufficient_provenance` | 1,192 | 20.9% |
| `in_repo_unresolvable` | 1,014 | 17.8% |
| `unclassified_persisted_drop` | 222 | 3.9% |
| `external_likely` | 3 | 0.1% |

## Language Funnel

| Language | Observed | Filtered | Persisted | Accepted | Dropped | Persisted acceptance | Observed retention |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Java | 43,954 | 1,525 | 42,429 | 41,776 | 653 | 98.46% | 96.53% |
| JavaScript | 3,797 | 223 | 3,574 | 3,490 | 84 | 97.65% | 94.13% |
| Python | 92,154 | 28,112 | 64,042 | 62,898 | 1,144 | 98.21% | 69.49% |
| TypeScript | 157,691 | 10,549 | 147,142 | 143,329 | 3,813 | 97.41% | 93.31% |

Takeaways:

- TypeScript dominates scale.
- Python has the largest pre-persist reduction by volume.
- Persisted acceptance remains high in every language aggregate despite funnel differences.

## Repository Takeaways

### `vscode` dominates persisted scale

- 145,243 persisted callsites
- 155,451 observed syntactic callsites
- 10,208 filtered before persistence
- 141,486 persisted accepted
- 3,757 persisted dropped

`vscode` is the main driver of aggregate TypeScript behavior and of overall persisted drop volume.

### `fastapi` is the main persisted-acceptance outlier

- 2,310 observed
- 1,078 filtered before persistence
- 1,232 persisted
- 716 accepted
- 516 dropped
- 58.12% persisted acceptance

This is the only repository whose persisted working-set acceptance is a clear outlier.

### `sympy` has the largest pre-persist filter volume

- 72,663 observed
- 25,344 filtered before persistence
- 47,319 persisted
- 47,109 accepted
- 210 dropped

`sympy` is the strongest example of why the funnel matters. It has a large observed-to-persisted reduction but an excellent persisted acceptance rate once inside the working set.

### `webpack` is the main structural-density warning case

`webpack` is the only repo whose aggregate structural density raises an explicit warning. That warning is about file mix and low-node files, not about callsite funnel integrity.

## Pre-Persist Buckets: Current Limitation

The published reports include `filtered_pre_persist_buckets`, but in this stored validation set they are still empty.

That means:

- the volume of pre-persist filtering is available and reliable
- the reason breakdown for that filtering is not yet informative in these stored artifacts

So the current validation set can answer:
- how much was observed
- how much was filtered before persistence
- how much survived into persisted `call_sites`
- how persisted dropped rows break down

But it cannot answer:
- why the 40,409 pre-persist filtered rows were filtered, beyond their volume

Refreshing the validation reports after the new bucket-emission changes is the next step if that breakdown is needed in published validation material.

## Build Performance

Observed wall-clock build times for the 10 repositories:

| Metric | Value |
| --- | ---: |
| Fastest | 2.93 s (`axios`) |
| Median | 30.70 s |
| Mean | 103.63 s |
| Slowest | 645.94 s (`vscode`) |
| Fastest per 1K nodes | 1.24 s (`pydantic`) |
| Median per 1K nodes | 2.13 s |
| Mean per 1K nodes | 2.73 s |
| Slowest per 1K nodes | 5.98 s (`vscode`) |

## What This Validation Now Supports

These reports support the following claims:

- SCIONA scales to large mixed-language repositories.
- The persisted `call_sites` working set resolves at high rates across the published validation set.
- Persisted drop volume is dominated by ambiguity and provenance issues rather than obvious external leakage.
- The observed-to-persisted funnel is measurable and should be reported separately from persisted acceptance.

These reports do not claim:
- a theoretical callsite completeness
- that all pre-persist filtered rows are external or standard-library
- runtime or semantic correctness claims beyond deterministic structural acceptance rules
