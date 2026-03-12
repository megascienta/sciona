# SCIONA Build Status Validation Report

This document summarizes the JSON reports stored under `validations/build_status_reports/reports/`, generated between **2026-03-11 22:29 UTC and 22:44 UTC**.

The current dataset contains **10 repositories** and reflects `tool_version = 0.1.0.dev789`, `schema_version = 1.0`, and `status_report_version = 1`.

## Dataset Scope

Repositories covered:

* [`airbyte`](https://github.com/airbytehq/airbyte)
* [`axios`](https://github.com/axios/axios)
* [`commons-lang`](https://github.com/apache/commons-lang)
* [`fastapi`](https://github.com/fastapi/fastapi)
* [`guava`](https://github.com/google/guava)
* [`nest`](https://github.com/nestjs/nest)
* [`pydantic`](https://github.com/pydantic/pydantic)
* [`sympy`](https://github.com/sympy/sympy)
* [`vscode`](https://github.com/microsoft/vscode)
* [`webpack`](https://github.com/webpack/webpack)

The source artifacts are the JSON outputs (`validations/build_status_reports/reports/`) produced by:

```bash
sciona status --output ...
```

The current report is based on the `summary` payloads inside those files.

## Headline Results

| Metric | Value |
| --- | ---: |
| Indexed files | 27,700 |
| Discovered files | 27,711 |
| Structural nodes | 291,891 |
| Structural edges | 368,329 |
| Eligible call sites | 260,361 |
| Accepted call edges | 251,046 |
| Dropped call sites | 9,315 |
| Raw call-edge success | 96.42% |
| Non-test success | 96.84% |
| Test success | 95.18% |
| Adjusted success (`external_likely` excluded) | 96.43% |
| `external_likely` exclusions | 27 |
| `in_repo_unresolvable` drops | 5,985 |

Eligible call sites represent candidate in-repository calls identified by the
deterministic resolver. Accepted call edges are those successfully resolved to
a concrete in-repository target. SCIONA resolves **96.42%** of candidate in-repository calls across tested repositories using purely deterministic structural analysis. Candidate calls are those whose syntactic context indicates a potential in-repository target. `external_likely` are in-repository call candidates which potentilly refer to external sources. The adjustment for `external_likely` is negligible:

```text
27 exclusions out of 260,361 eligible call sites = 0.01%
```

## Build Performance

Observed wall-clock build times for the 10 repository builds:

| Metric | Value |
| --- | ---: |
| Fastest | 3.06 s (`axios`) |
| Median | 29.59 s |
| Mean | 95.97 s |
| Slowest | 593.50 s (`vscode`) |
| Fastest per 1K nodes | 1.20 s (`pydantic`) |
| Median per 1K nodes | 2.05 s |
| Mean per 1K nodes | 2.63 s |
| Slowest per 1K nodes | 5.49 s (`vscode`) |

For the nine non-VSCode repositories, wall time ranged from **3.06 s** to **129.73 s**, with a median of **15.90 s**. The average is heavily skewed by the `vscode` repository.

| Repo | Wall time | per 1K nodes |
| --- | ---: | ---: |
| airbyte | 52.48 s | 2.08 s |
| axios | 3.06 s | 5.31 s |
| commons-lang | 15.59 s | 1.35 s |
| fastapi | 10.12 s | 1.53 s |
| guava | 83.10 s | 1.30 s |
| nest | 12.92 s | 2.01 s |
| pydantic | 15.90 s | 1.20 s |
| sympy | 129.73 s | 3.17 s |
| vscode | 593.50 s | 5.49 s |
| webpack | 43.27 s | 2.90 s |

## Language Rollup

| Language | Files | Nodes | Edges | Eligible | Accepted | Dropped | Raw % | Non-tests % | Tests % | Adjusted % | Adj Excluded |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Java | 4,251 | 79,844 | 82,648 | 45,603 | 41,330 | 4,273 | 90.63 | 93.38 | 85.79 | 90.68 | 24 |
| JavaScript | 8,991 | 15,838 | 12,126 | 3,574 | 3,490 | 84 | 97.65 | 97.70 | 97.26 | 97.70 | 2 |
| Python | 6,046 | 81,834 | 94,157 | 64,042 | 62,898 | 1,144 | 98.21 | 98.91 | 97.26 | 98.22 | 1 |
| TypeScript | 8,412 | 114,375 | 179,398 | 147,142 | 143,328 | 3,814 | 97.41 | 97.02 | 99.61 | 97.41 | 0 |

Language-level takeaways:

* Python is currently the strongest cohort at **98.21%** raw success.
* TypeScript carries most of the call-site volume: **147,142 eligible** out of **260,361** total.
* Java is still the language cohort at **90.63%**, but its non-test success is materially better at **93.38%**.
* JavaScript is at **97.65%**, though some repositories (for example `webpack`) contain many low-node files due to configuration and fixture trees.

## Repository Breakdown

### `airbyte`

Wall time: **52.48 s**. **2.08 s per 1K nodes**. Mixed-language repository; almost all adjusted exclusions come from Java.

| Language | Files | Nodes | Edges | Eligible | Accepted | Dropped | Raw % | Non-tests % | Tests % | `external_likely` | `in_repo_unresolvable` | Low-node files % | Warnings |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| java | 473 | 4,144 | 3,829 | 1,641 | 1,585 | 56 | 96.59 | 95.42 | 99.57 | 24 | 9 | 0.00 | - |
| javascript | 44 | 147 | 127 | 53 | 53 | 0 | 100.00 | 100.00 | n/a | 0 | 0 | 20.45 | - |
| python | 2,768 | 20,976 | 20,488 | 13,106 | 12,830 | 276 | 97.89 | 97.90 | 97.32 | 1 | 262 | 26.16 | - |
| typescript | 3 | 8 | 6 | 2 | 2 | 0 | 100.00 | 100.00 | n/a | 0 | 0 | 33.33 | - |

### `axios`

Wall time: **3.06 s**. **5.31 s per 1K nodes**. Tiny JS-heavy repository with many minimal files.

| Language | Files | Nodes | Edges | Eligible | Accepted | Dropped | Raw % | Non-tests % | Tests % | `external_likely` | `in_repo_unresolvable` | Low-node files % | Warnings |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| javascript | 167 | 438 | 510 | 165 | 161 | 4 | 97.58 | 97.47 | 100.00 | 0 | 2 | 55.09 | - |
| typescript | 6 | 138 | 132 | 0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 | 50.00 | - |

### `commons-lang`

Wall time: **15.59 s**. **1.35 s per 1K nodes**. Test-heavy Java usage is the main drag on the repo aggregate.

| Language | Files | Nodes | Edges | Eligible | Accepted | Dropped | Raw % | Non-tests % | Tests % | `external_likely` | `in_repo_unresolvable` | Low-node files % | Warnings |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| java | 534 | 11,566 | 11,603 | 5,647 | 5,327 | 320 | 94.33 | 97.04 | 90.28 | 0 | 90 | 4.87 | - |

### `fastapi`

Wall time: **10.12 s**. **1.53 s per 1K nodes**. Strong non-test Python resolution, but tests dominate the drop volume.

| Language | Files | Nodes | Edges | Eligible | Accepted | Dropped | Raw % | Non-tests % | Tests % | `external_likely` | `in_repo_unresolvable` | Low-node files % | Warnings |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| javascript | 3 | 25 | 22 | 22 | 22 | 0 | 100.00 | 100.00 | n/a | 0 | 0 | 0.00 | - |
| python | 1,284 | 6,579 | 7,016 | 1,210 | 694 | 516 | 57.36 | 98.40 | 34.07 | 0 | 415 | 16.43 | - |

### `guava`

Wall time: **83.10 s**. **1.30 s per 1K nodes**. Largest Java drop volume in the dataset.

| Language | Files | Nodes | Edges | Eligible | Accepted | Dropped | Raw % | Non-tests % | Tests % | `external_likely` | `in_repo_unresolvable` | Low-node files % | Warnings |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| java | 3,243 | 64,129 | 67,212 | 38,315 | 34,418 | 3,897 | 89.83 | 92.78 | 84.60 | 0 | 2,580 | 4.44 | - |
| javascript | 2 | 2 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 | 100.00 | `low_node_file_ratio_high` |

### `nest`

Wall time: **12.92 s**. **2.01 s per 1K nodes**. Small TypeScript surface with consistently high resolution.

| Language | Files | Nodes | Edges | Eligible | Accepted | Dropped | Raw % | Non-tests % | Tests % | `external_likely` | `in_repo_unresolvable` | Low-node files % | Warnings |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| javascript | 49 | 61 | 17 | 2 | 2 | 0 | 100.00 | 100.00 | n/a | 0 | 0 | 89.80 | `low_node_file_ratio_high` |
| typescript | 1,659 | 6,355 | 7,988 | 2,009 | 1,950 | 59 | 97.06 | 97.05 | 100.00 | 0 | 40 | 29.54 | - |

### `pydantic`

Wall time: **15.90 s**. **1.20 s per 1K nodes**. Test scope is the main source of drops.

| Language | Files | Nodes | Edges | Eligible | Accepted | Dropped | Raw % | Non-tests % | Tests % | `external_likely` | `in_repo_unresolvable` | Low-node files % | Warnings |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| javascript | 6 | 16 | 10 | 8 | 8 | 0 | 100.00 | 100.00 | 100.00 | 0 | 0 | 66.67 | `low_node_file_ratio_high` |
| python | 401 | 13,285 | 14,009 | 2,407 | 2,265 | 142 | 94.10 | 97.52 | 88.11 | 0 | 64 | 7.98 | - |

### `sympy`

Wall time: **129.73 s**. **3.17 s per 1K nodes**. Best large-repository resolution rate in the dataset.

| Language | Files | Nodes | Edges | Eligible | Accepted | Dropped | Raw % | Non-tests % | Tests % | `external_likely` | `in_repo_unresolvable` | Low-node files % | Warnings |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| python | 1,590 | 40,980 | 52,633 | 47,319 | 47,109 | 210 | 99.56 | 99.61 | 99.51 | 0 | 139 | 13.71 | - |

### `vscode`

Wall time: **593.50 s**. **5.49 s per 1K nodes**. Largest repository and largest TypeScript volume by far.

| Language | Files | Nodes | Edges | Eligible | Accepted | Dropped | Raw % | Non-tests % | Tests % | `external_likely` | `in_repo_unresolvable` | Low-node files % | Warnings |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| java | 1 | 5 | 4 | 0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 | 0.00 | - |
| javascript | 105 | 392 | 291 | 124 | 121 | 3 | 97.58 | 98.84 | 94.74 | 2 | 0 | 61.90 | `low_node_file_ratio_high` |
| python | 3 | 14 | 11 | 0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 | 33.33 | - |
| typescript | 6,656 | 107,686 | 171,168 | 145,119 | 141,364 | 3,755 | 97.41 | 97.02 | 99.61 | 0 | 2,365 | 21.66 | - |

### `webpack`

Wall time: **43.27 s**. **2.90 s per 1K nodes**. The only repository whose aggregate structural density raises a warning.

| Language | Files | Nodes | Edges | Eligible | Accepted | Dropped | Raw % | Non-tests % | Tests % | `external_likely` | `in_repo_unresolvable` | Low-node files % | Warnings |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| javascript | 8,615 | 14,757 | 11,149 | 3,200 | 3,123 | 77 | 97.59 | 97.62 | 97.44 | 0 | 19 | 83.93 | `low_node_file_ratio_high` |
| typescript | 88 | 188 | 104 | 12 | 12 | 0 | 100.00 | 100.00 | n/a | 0 | 0 | 63.64 | `low_node_file_ratio_high` |

## What Stands Out

### 1. `vscode` dominates scale

`vscode` alone contributes:

* **145,243 / 260,361** eligible call sites (**55.8%** of the dataset)
* **141,485 / 251,046** accepted call edges (**56.4%** of the dataset)
* **108,097 / 291,891** nodes (**37.0%** of the dataset)

Any aggregate trend in this report is therefore strongly influenced by the TypeScript-heavy VSCode result set.

### 2. `fastapi` is the only true raw-rate outlier

`fastapi` records:

* **58.12%** raw success
* **98.48%** non-test success
* **34.07%** test success

This split suggests that the low aggregate rate is primarily driven by test-suite patterns rather than library code.

### 3. Java remains the main source of unresolved volume

Java contributes **4,273** dropped call sites, nearly half of all drops in the dataset. Most of this volume comes from `guava`, which contains extensive test suites and heavy use of interface dispatch and method overloading.

### 4. Structural-density warnings are mostly benign except for webpack

Across all discovered files, **10,795 / 27,711** files (**38.96%**) have one or fewer structural nodes. That sounds alarming in aggregate, but only one repository trips the explicit inflation warning:

* `webpack`: `low_node_file_ratio = 83.73%`, `inferred_zero_node_files = 11`, warning `low_node_file_ratio_high`

This appears high in aggregate, but most cases correspond to configuration, fixture, or minimal modules that naturally produce few structural nodes.

## Interpretation Boundary

These reports still support the same high-level conclusion:

* SCIONA resolves in-repository call edges at high rates on Python, JavaScript, and TypeScript codebases.
* Java remains meaningfully harder under the current deterministic, syntax-only rules.
* Aggregate results should be read with repo composition in mind, especially the heavy influence of `vscode`, the test-heavy failure mode in `fastapi`, and the fixture-heavy file mix in `webpack`.

The numbers above should be interpreted as structural diagnostics. They do not claim:
* runtime correctness
* semantic precision beyond the deterministic acceptance rules
* recovery of dynamic dispatch