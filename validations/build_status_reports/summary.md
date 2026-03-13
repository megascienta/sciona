# SCIONA Build Status Validation Summary

This summary consolidates the regenerated `sciona status --json` reports under
`validations/build_status_reports/reports/` for these repositories:

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

Hardware used for these runs:

- `MacBook Pro 2019, Intel Core i9 2.4 GHz`

## Quantity Definitions

Structural quantities:

- `files`: tracked source files included in the committed snapshot for enabled
  languages
- `nodes`: structural nodes persisted in CoreDB for the committed snapshot
- `edges`: structural CoreDB edges persisted for the committed snapshot

Callsite funnel quantities:

- `observed_syntactic_callsites`: syntactic call observations emitted for the
  committed snapshot before pre-persist filtering
- `filtered_pre_persist`: observed callsites excluded before persisted callsite
  retention
- `persisted_callsites`: retained callsite observations after pre-persist
  filtering
- `persisted_accepted`: retained callsite observations whose strict resolution
  outcome is accepted
- `persisted_dropped`: retained callsite observations whose strict resolution
  outcome is dropped

Pre-persist filter buckets:

- `no_in_repo_candidate_terminal`: no in-repo candidate materialized for a
  terminal identifier
- `no_in_repo_candidate_qualified`: no in-repo candidate materialized for a
  qualified identifier
- `accepted_outside_in_repo`: an accepted row pointed outside the in-repo
  callable set
- `invalid_observation_shape`: malformed or internally inconsistent call
  observation row shape

Pair and edge quantities:

- `callsite_pairs`: persisted deduplicated in-scope candidate caller-to-callee
  pairs
- `finalized_call_edges`: deduplicated finalized callable-to-callable edges
  derived from `callsite_pairs`

Pair-expansion quantities:

- `persisted_callsites_with_zero_pairs`: retained callsite observations that
  materialized zero persisted pairs
- `persisted_callsites_with_one_pair`: retained callsite observations that
  materialized exactly one persisted pair
- `persisted_callsites_with_multiple_pairs`: retained callsite observations
  that materialized more than one persisted pair
- `pair_expansion_factor`: `callsite_pairs / persisted_callsites`
- `multi_pair_share`: `persisted_callsites_with_multiple_pairs / persisted_callsites`
- `max_pairs_for_single_persisted_callsite`: maximum number of persisted pairs
  produced by one retained callsite observation

Scope quantities:

- `non_tests`: rows attributed to non-test files
- `tests`: rows attributed to test files

Timing quantities:

- `build_total_seconds`: persisted inner build metric for the committed build
- `build_wall_seconds`: persisted end-to-end command wall time
- `build_phase_timings.compute_build_fingerprint`
- `build_phase_timings.discover_files`
- `build_phase_timings.prepare_snapshots`
- `build_phase_timings.register_modules`
- `build_phase_timings.build_structural_index`
- `build_phase_timings.derive_call_artifacts`
- `build_phase_timings.prepare_callsite_pairs`
- `build_phase_timings.write_callsite_pairs`
- `build_phase_timings.rebuild_graph_index`
- `build_phase_timings.rebuild_graph_rollups`

## Dataset Totals

| Quantity | Value |
| --- | ---: |
| Repositories | `10` |
| Files | `27,700` |
| Nodes | `291,891` |
| Edges | `368,329` |
| Observed syntactic callsites | `297,596` |
| Filtered pre-persist | `40,409` |
| Persisted callsites | `257,187` |
| Persisted accepted | `251,493` |
| Persisted dropped | `5,694` |
| Callsite pairs | `288,781` |
| Finalized call edges | `285,632` |
| Persisted callsites with zero pairs | `2,431` |
| Persisted callsites with one pair | `251,493` |
| Persisted callsites with multiple pairs | `3,263` |
| Max pairs for one persisted callsite | `1,253` |
| Pair expansion factor | `1.1228` |
| Multi-pair share | `0.0127` |

Funnel conservation identity:

```text
observed_syntactic_callsites = filtered_pre_persist + persisted_callsites
297,596 = 40,409 + 257,187
```

Dataset-level pre-persist buckets:

| Bucket | Count |
| --- | ---: |
| `no_in_repo_candidate_qualified` | `40,409` |

## Scope Totals

Callsite pairs by scope:

| Scope | Count |
| --- | ---: |
| `non_tests` | `223,707` |
| `tests` | `65,074` |

Finalized call edges by scope:

| Scope | Count |
| --- | ---: |
| `non_tests` | `221,074` |
| `tests` | `64,558` |

## Per-Language Totals

| Language | Files | Nodes | Edges | Observed | Filtered | Persisted | Accepted | Dropped | Pairs | Finalized edges |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `java` | `4,251` | `79,844` | `82,648` | `43,954` | `1,525` | `42,429` | `41,776` | `653` | `43,385` | `43,345` |
| `javascript` | `8,991` | `15,838` | `12,126` | `3,797` | `223` | `3,574` | `3,490` | `84` | `3,550` | `3,534` |
| `python` | `6,046` | `81,834` | `94,157` | `92,154` | `28,112` | `64,042` | `62,898` | `1,144` | `62,898` | `61,498` |
| `typescript` | `8,412` | `114,375` | `179,398` | `157,691` | `10,549` | `147,142` | `143,329` | `3,813` | `178,948` | `177,255` |

Per-language pair-expansion totals:

| Language | Zero pairs | One pair | Multiple pairs | Max pairs | Pair expansion factor | Multi-pair share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `java` | `225` | `41,776` | `428` | `34` | `1.0225` | `0.0101` |
| `javascript` | `63` | `3,490` | `21` | `5` | `0.9933` | `0.0059` |
| `python` | `1,144` | `62,898` | `0` | `1` | `0.9821` | `0.0000` |
| `typescript` | `999` | `143,329` | `2,814` | `1,253` | `1.2162` | `0.0191` |

Per-language scope totals:

| Language | Non-test pairs | Test pairs | Non-test edges | Test edges |
| --- | ---: | ---: | ---: | ---: |
| `java` | `28,969` | `14,416` | `28,929` | `14,416` |
| `javascript` | `3,124` | `426` | `3,108` | `426` |
| `python` | `36,597` | `26,301` | `35,700` | `25,798` |
| `typescript` | `155,017` | `23,931` | `153,337` | `23,918` |

## Per-Repository Totals

| Repository | Files | Nodes | Edges | Observed | Filtered | Persisted | Accepted | Dropped | Pairs | Finalized edges |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `airbyte` | `3,288` | `25,275` | `24,450` | `15,626` | `896` | `14,730` | `14,441` | `289` | `14,453` | `13,613` |
| `axios` | `173` | `576` | `642` | `231` | `66` | `165` | `161` | `4` | `165` | `163` |
| `commons-lang` | `534` | `11,566` | `11,603` | `5,692` | `205` | `5,487` | `5,376` | `111` | `5,718` | `5,713` |
| `fastapi` | `1,287` | `6,604` | `7,038` | `2,310` | `1,078` | `1,232` | `716` | `516` | `716` | `716` |
| `guava` | `3,245` | `64,131` | `67,212` | `36,639` | `1,266` | `35,373` | `34,844` | `529` | `36,099` | `36,064` |
| `nest` | `1,708` | `6,416` | `8,005` | `2,353` | `342` | `2,011` | `1,952` | `59` | `2,203` | `2,195` |
| `pydantic` | `407` | `13,301` | `14,019` | `3,263` | `848` | `2,415` | `2,273` | `142` | `2,273` | `2,264` |
| `sympy` | `1,590` | `40,980` | `52,633` | `72,663` | `25,344` | `47,319` | `47,109` | `210` | `47,109` | `46,558` |
| `vscode` | `6,765` | `108,097` | `171,474` | `155,451` | `10,208` | `145,243` | `141,486` | `3,757` | `176,856` | `175,171` |
| `webpack` | `8,703` | `14,945` | `11,253` | `3,368` | `156` | `3,212` | `3,135` | `77` | `3,189` | `3,175` |

Per-repository pair-expansion and scope totals:

| Repository | Zero pairs | One pair | Multiple pairs | Max pairs | Non-test pairs | Test pairs | Non-test edges | Test edges |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `airbyte` | `283` | `14,441` | `6` | `2` | `13,848` | `605` | `13,008` | `605` |
| `axios` | `2` | `161` | `2` | `2` | `158` | `7` | `156` | `7` |
| `commons-lang` | `42` | `5,376` | `69` | `10` | `3,667` | `2,051` | `3,662` | `2,051` |
| `fastapi` | `516` | `716` | `0` | `1` | `453` | `263` | `453` | `263` |
| `guava` | `176` | `34,844` | `353` | `34` | `24,194` | `11,905` | `24,159` | `11,905` |
| `nest` | `14` | `1,952` | `45` | `16` | `2,196` | `7` | `2,188` | `7` |
| `pydantic` | `142` | `2,273` | `0` | `1` | `1,499` | `774` | `1,499` | `765` |
| `sympy` | `210` | `47,109` | `0` | `1` | `21,987` | `25,122` | `21,930` | `24,628` |
| `vscode` | `987` | `141,486` | `2,770` | `1,253` | `152,896` | `23,960` | `151,224` | `23,947` |
| `webpack` | `59` | `3,135` | `18` | `5` | `2,809` | `380` | `2,795` | `380` |

Per-repository pre-persist buckets:

| Repository | `no_in_repo_candidate_qualified` |
| --- | ---: |
| `airbyte` | `896` |
| `axios` | `66` |
| `commons-lang` | `205` |
| `fastapi` | `1,078` |
| `guava` | `1,266` |
| `nest` | `342` |
| `pydantic` | `848` |
| `sympy` | `25,344` |
| `vscode` | `10,208` |
| `webpack` | `156` |

## Build Timing Totals

| Quantity | Value |
| --- | ---: |
| Mean build total seconds | `118.14 s` |
| Median build total seconds | `32.27 s` |
| Mean build wall seconds | `120.40 s` |
| Median build wall seconds | `33.86 s` |

Per-repository build totals:

| Repository | Build total seconds |
| --- | ---: |
| `airbyte` | `67.59` |
| `axios` | `2.79` |
| `commons-lang` | `19.17` |
| `fastapi` | `11.05` |
| `guava` | `166.98` |
| `nest` | `15.89` |
| `pydantic` | `20.87` |
| `sympy` | `165.44` |
| `vscode` | `667.97` |
| `webpack` | `43.67` |

Average phase timings:

| Phase key | Mean seconds |
| --- | ---: |
| `compute_build_fingerprint` | `0.34` |
| `discover_files` | `1.26` |
| `prepare_snapshots` | `0.58` |
| `register_modules` | `1.12` |
| `build_structural_index` | `29.22` |
| `derive_call_artifacts` | `27.97` |
| `prepare_callsite_pairs` | `33.55` |
| `write_callsite_pairs` | `3.25` |
| `rebuild_graph_index` | `1.90` |
| `rebuild_graph_rollups` | `1.52` |

Per-repository phase timings:

| Repository | Fingerprint | Discover | Snapshots | Modules | Structural index | Call observations | Prepare pairs | Write pairs | Graph index | Graph rollups |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `airbyte` | `0.76` | `3.64` | `0.99` | `2.08` | `26.15` | `20.00` | `0.87` | `0.63` | `0.76` | `0.83` |
| `axios` | `0.22` | `0.18` | `0.03` | `0.06` | `0.80` | `0.76` | `0.01` | `0.01` | `0.01` | `0.01` |
| `commons-lang` | `0.25` | `0.34` | `0.12` | `0.22` | `7.46` | `6.36` | `0.30` | `0.24` | `0.28` | `0.32` |
| `fastapi` | `0.25` | `0.53` | `0.22` | `0.38` | `3.78` | `3.28` | `0.13` | `0.04` | `0.12` | `0.12` |
| `guava` | `0.38` | `1.30` | `0.80` | `1.48` | `45.63` | `49.56` | `7.62` | `12.60` | `3.58` | `3.59` |
| `nest` | `0.28` | `0.65` | `0.35` | `0.65` | `5.55` | `4.92` | `0.18` | `0.07` | `0.17` | `0.19` |
| `pydantic` | `0.27` | `0.30` | `0.09` | `0.16` | `8.20` | `7.19` | `0.18` | `0.09` | `0.35` | `0.39` |
| `sympy` | `0.27` | `0.74` | `0.35` | `0.65` | `46.28` | `51.82` | `38.32` | `3.22` | `2.53` | `1.83` |
| `vscode` | `0.44` | `2.65` | `1.39` | `2.70` | `135.00` | `121.09` | `287.70` | `15.49` | `10.96` | `7.59` |
| `webpack` | `0.30` | `2.26` | `1.45` | `2.84` | `13.36` | `14.74` | `0.16` | `0.09` | `0.24` | `0.28` |
