# SCIONA Developer Guide

This guide is operational. It explains where code lives, how the current build
path works, and how to validate changes against the codebase as it exists now.

Authoritative references:

- Normative contract: `docs/CONTRACT.md`
- Generated capabilities: `docs/CAPABILITY_MANIFEST.json`
- Executable parity contract:
  `src/sciona/code_analysis/languages/common/support/parity_contract.py`

If this guide conflicts with `CONTRACT.md`, the contract wins.

## Scope

Use this document for:

- repository boundaries and ownership;
- current extraction, storage, reducer, and CLI layout;
- build, artifact, and diff-overlay mechanics;
- public addon API boundaries;
- required test workflow.

Do not use this document to redefine structural semantics.

## Runtime

- Python: `>=3.11,<3.13`
- Required runtime dependencies include `tree_sitter`, `tree_sitter_languages`,
  `typer`, `click`, `pyyaml`, `pathspec`, and `networkx`

## Repository Boundaries

- `src/sciona/cli/`: Typer CLI entrypoint and UX shell over `pipelines.ops.*`
  for `build`, `init`, `agents`, `hooks`, `status`, `clean`, `search`,
  `resolve`, and `reducer` command wiring
- `src/sciona/api/`: stable public addon-facing namespace; public root exports
  only `sciona.api.addons` and must not carry CLI-only bridge surfaces
- `src/sciona/runtime/`: paths, config loading, logging, git helpers, time,
  reducer metadata, addon API version contract, shared constants, and runtime
  overlay-facing types; canonical overlay computation/patching does not live
  here
- `src/sciona/data_storage/core_db/`: committed structural snapshot schema and
  read/write operations
- `src/sciona/data_storage/artifact_db/`: reducer-facing query storage for call
  artifacts, graph projections, reporting, overlay state, rollups, and
  maintenance
- `src/sciona/data_storage/connections.py`: read/write connection helpers used
  across pipelines, reducers, and addon API helpers
- `src/sciona/code_analysis/core/`: build engine, analyzer routing, snapshot
  creation, structural assembly, parser bootstrap, and extraction contracts
- `src/sciona/code_analysis/languages/builtin/`: builtin analyzers for
  `python`, `typescript`, `javascript`, and `java`
- `src/sciona/code_analysis/languages/common/`: shared query surfaces, parity
  contract, capabilities, naming, scope, and reducer-facing language helpers
- `src/sciona/code_analysis/artifacts/`: artifact re-analysis, call artifact
  derivation, and rollup generation against committed structural state
- `src/sciona/code_analysis/tools/`: discovery, call extraction, query/profile
  tooling, snapshots, and related helpers
- `src/sciona/pipelines/domain/`: immutable repo, policy, and snapshot decision
  objects
- `src/sciona/pipelines/policy/`: repo and snapshot policy checks plus build
  policy resolution
- `src/sciona/pipelines/exec/`: execution-layer orchestration for build,
  reporting, repo checks, init dialog, guardrails, and fingerprint reuse
- `src/sciona/pipelines/diff_overlay/`: canonical dirty-worktree overlay
  computation, sorting, patching, and summary payload generation
- `src/sciona/pipelines/ops/reducers.py`: reducer listing and emission
  workflow; `ops` modules own repo-state resolution and policy-aware workflow
  entrypoints while `exec` modules own mechanism over resolved `RepoState`
- `src/sciona/reducers/`: reducer implementations; shared reducer helpers are
  grouped under `src/sciona/reducers/helpers/shared/`,
  `src/sciona/reducers/helpers/artifact/`, and
  `src/sciona/reducers/helpers/impl/`
- Reducers may depend on canonical overlay patching helpers under
  `src/sciona/pipelines/diff_overlay/patching/`; broader pipeline workflow
  imports remain out of bounds for reducer modules
- High-traffic orientation and coupling reducers may expose a compact mode for
  agent-facing orientation. Prefer compact output first for ownership,
  dependency, and migration-scope questions; switch to full payloads only when
  the compact view is insufficient.
- Compact-capable reducers should expose a first-class `compact` flag rather
  than relying on truncation alone. Compact payloads should use
  `payload_kind: "compact_summary"` and preserve the filter context, headline
  totals, and bounded preview blocks needed for agent decisions.
- `tests/`: API, code-analysis, data-storage, pipeline, reducer, and runtime
  coverage

Core dependency direction is still downward by layer, but artifact and overlay
modules are first-class parts of the current implementation and should not be
treated as optional sidecars.

## Language Adapter Architecture

Pipeline:

```text
committed source snapshot
  -> structural extraction
  -> nodes / structural edges
  -> CoreDB model
  -> callsite observation
  -> observed_syntactic_callsites
  -> pre-persist filtering
  -> persisted_callsites
  -> candidate materialization
  -> callsite_pairs
  -> graph collapse
  -> node_calls
  -> ArtifactDB model
  -> reducer-facing projections
  -> overlay support
```

Current adapter contract is `AdapterSpecV1` in
`src/sciona/code_analysis/core/extract/interfaces/language_adapter.py`.

Required descriptor fields:

- `language_id`
- `extensions`
- `grammar_name`
- `query_set_version`
- `callable_types`
- `module_namer`
- `extractor_factory`
- `capability_manifest_key`

Implementation notes:

- `declared` is the default callable role for named structural callable
  declarations that are neither nested, nor promoted from stable bindings, nor
  constructors
- Python direct class inheritance emits `EXTENDS`; Python does not emit a
  distinct `IMPLEMENTS` edge
- JavaScript and TypeScript use independent walker, import extraction, and
  call resolution implementations; only language-agnostic infrastructure and
  declarative query/capability registries are shared
- Parser bootstrap is isolated in
  `src/sciona/code_analysis/core/extract/parsing/parser_bootstrap.py`
- Query helpers stay separate in
  `src/sciona/code_analysis/core/extract/parsing/query_helpers.py`
- Strict call candidate selection is defined in
  `src/sciona/code_analysis/analysis_contracts/strict_call_contract.py` and
  batched/used by artifact-layer call resolution in
  `src/sciona/code_analysis/analysis_contracts/strict_call_resolution.py` and
  `src/sciona/code_analysis/artifacts/call_resolution.py`; Core structural
  assembly does not finalize calls
- Reducer-facing `CALLS`, callsite pairs, graph edges, fan stats, and rollups are
  finalized in ArtifactDB, not served directly from CoreDB `edges`

Supported structural carriers:

- Python structural nodes are limited to
  `decorated_definition`, `class_definition`, `function_definition`,
  `assignment`, and `augmented_assignment`; the only supported wrapper carrier
  is `expression_statement` for stable bound-callable assignments
- TypeScript structural nodes are limited to class-like declarations,
  callable declarations, `variable_declarator`, `public_field_definition`, and
  `assignment_expression`; supported wrapper carriers are `export_statement`,
  `statement_block`, `class_body`, `lexical_declaration`, and
  `expression_statement`
- JavaScript structural nodes are limited to class/function declarations,
  method definitions, stable binding nodes, and `assignment_expression`;
  supported wrapper carriers are `export_statement`, `statement_block`,
  `class_body`, `lexical_declaration`, and `expression_statement`
- Java structural traversal is direct-only; it does not rely on wrapper carrier
  nodes beyond the declared structural node types
- Unsupported wrappers and callback-only containers are intentionally
  fail-closed: they may suppress structural discovery until an explicit query
  surface is added

## Build Lifecycle

`src/sciona/pipelines/exec/build.py` is the current high-level build path:

1. Create snapshot metadata and compute a build fingerprint.
2. Build the committed CoreDB structural snapshot inside one transaction.
3. Canonicalize and commit the singleton structural snapshot.
4. Rebuild ArtifactDB when artifact refresh is enabled.
5. Persist build/reporting metadata for reuse and status reporting.

`BuildEngine` in `src/sciona/code_analysis/core/engine.py` currently owns:

- tracked/ignored path collection via git helpers;
- discovery filtering through `discovery.exclude_globs`;
- file-size, node-count, and call-identifier limits;
- analyzer dispatch, degraded module retention for per-file analysis failures,
  and `parse_failures` accounting;
- accumulation of import and call-gate diagnostics.

`build_artifacts_for_snapshot()` in
`src/sciona/pipelines/ops/build_artifacts.py` currently owns:

- artifact re-analysis through `ArtifactEngine`;
- per-file warning-and-continue artifact derivation when an eligible file
  cannot be re-analyzed;
- full reset of derived ArtifactDB state before repopulation;
- `callsite_pairs` and `node_calls` materialization;
- rebuild of reducer-facing graph edges and rollups;
- rebuild-status metadata and diagnostics persistence;
- overlay table clearing before fresh artifact population.

Current user-visible build phases are:

- `Computing build fingerprint`
- `Discovering files`
- `Preparing snapshots`
- `Registering modules`
- `Building structural index`
- `Extracting call observations`
- `Preparing callsite pairs`
- `Writing callsite pairs`
- `Rebuilding call graph index`
- `Rebuilding graph rollups`
- `Diagnostic classification` when `sciona build --diagnostic` is enabled

Each phase now emits an elapsed duration in normal `sciona build` output after
that phase completes.

Timing semantics:

- CLI `sciona build` now reports `Wall time` as full command wall time
  from command start until final summary generation.
- When available, `Core build time` is also shown; this is the inner
  persisted build metric recorded by the build pipeline itself.
- The inner persisted metric includes core analysis, artifact analysis,
  artifact refresh, graph-index rebuild, and rollup rebuild.
- The inner persisted metric does not include later CLI-only work such as
  final summary querying or terminal rendering.
- `status --json` and `snapshot_report(...)` expose:
  - `build_total_seconds`: persisted inner build metric
  - `build_wall_seconds`: persisted full command wall time when it has already
    been recorded; callers must treat it as optional
  - `build_phase_timings`: persisted per-phase timing map
- During `sciona build`, wall time is rendered from the in-process command
  timer before `build_wall_seconds` persistence completes.
- `build_phase_timings` uses stable flat keys:
  - `compute_build_fingerprint`
  - `discover_files`
  - `prepare_snapshots`
  - `register_modules`
  - `build_structural_index`
  - `derive_call_artifacts`
  - `prepare_callsite_pairs`
  - `write_callsite_pairs`
  - `rebuild_graph_index`
  - `rebuild_graph_rollups`
  - `diagnostic_classification` only for diagnostic builds

Diagnostic build mode:

- `sciona build --diagnostic` adds an optional post-build phase that classifies
  rejected callsites into best-effort explanatory buckets for generated
  repo-root report artifacts
- `sciona build --diagnostic --verbose` also writes a repo-root verbose sidecar
  with bucketed callsite and file examples for investigation
- Diagnostic outputs are generated artifacts only; they are not persisted in
  CoreDB or ArtifactDB and they do not redefine canonical reducer-facing
  semantics
- Canonical DB-backed `sciona status --json` remains unchanged; diagnostic mode
  writes additional repo-root JSON files after the build completes
- Temporary diagnostic workspace files may be created under `.sciona` during
  the diagnostic phase and are removed before the build exits

## Snapshot and Artifact Semantics

- CoreDB keeps exactly one committed snapshot
- Snapshot ids are canonicalized from structural hash, git commit sha, and
  source
- CoreDB is the committed structural ingestion store
- When artifact refresh is enabled, ArtifactDB is rebuilt immediately after the
  committed snapshot and acts as the reducer-facing latest-state derived query
  store for that committed snapshot
- Reducers are expected to consume ArtifactDB projections when they exist, while
  still using CoreDB for identifier resolution and committed structural context
- Reducer-facing `CALLS` is finalized in ArtifactDB from artifact analysis, not
  from raw analyzer output alone
- Core/analyzer execution MAY observe the full syntactic callsite stream during
  extraction, but CoreDB MUST NOT resolve, accept, reject, or persist calls as
  structural facts
- Artifact processing owns pre-persistence callsite filtering and remains the
  authoritative source for reducer-facing `CALLS`
- `callsite_pairs` is the primary artifact-layer persisted working set of
  deduplicated in-scope candidate caller-to-callee pairs used for reporting and
  final call derivation; it is not the raw observed superset
  
- rejected callsites are publicly grouped as:
  `out_of_scope_call`, `weak_static_evidence`, `structural_gap`,
  `unclassified`
- bucket meanings:
  - `out_of_scope_call`: external, builtin, or structurally indirect/runtime
    call shapes outside the static in-repo contract target
  - `weak_static_evidence`: in-repo-looking call shapes whose structural
    evidence is still too weak for accepted static-in-repo status
  - `structural_gap`: malformed observations or clear parser/extraction/
    normalization deficiencies
  - `unclassified`: residual rejected callsites not explained by the other
    public buckets
- `status --json` exposes direct snapshot data only
- the public status payload is grouped as:
  - `labels`
  - `timing`
  - `totals`
  - `languages`
  - `scopes`
- `totals`, each language row, and each scope row use the same public sections:
  - `structure`
  - `callsites`
  - `pre_persist_filter`
  - `call_materialization`
- these public sections contain direct counts only:
  - `structure`: `files`, `nodes`, `edges`
  - `callsites`: `observed_syntactic_callsites`,
    `filtered_pre_persist`, `persisted_callsites`,
    `persisted_accepted`, `persisted_dropped`
  - `pre_persist_filter`: `out_of_scope_call`,
    `weak_static_evidence`, `structural_gap`, `unclassified`
  - `call_materialization`: `callsite_pairs`, `finalized_call_edges`
- `structure.files` and `structure.nodes` are structural counts from CoreDB
- `structure.edges` is the total reducer-facing graph edge count from
  ArtifactDB `graph_edges`, including structural edges and `CALLS`
- per-language and per-scope edge attribution is source-owned:
  each graph edge is counted under the language and scope of its source node
- `timing` remains top-level and contains:
  - `build_total_seconds`
  - `build_wall_seconds`
  - `build_phase_timings`
- derived ratios, warning flags, conservation checks, and expansion summaries
  are computed in evaluation notebooks, not emitted by `status --json`
- synthetic navigation nodes must use collision-safe identities that do not
  shadow or reuse canonical structural identities
- Fingerprint reuse can skip re-indexing even when a prior committed snapshot
  already exists
- Dirty-worktree overlay data is advisory and layered on top of reducer output;
  committed SCI remains authoritative
- `overlay_available` means overlay state exists for the reducer request; it does
  not always mean the reducer payload itself was patched to reflect dirty
  worktree state
- Some projections are intentionally metadata-only under overlay; they receive
  `_diff` annotations and warnings but remain committed-snapshot payloads

## DB Surfaces

Keep SQL details in code. Use this section for stable storage responsibilities.

CoreDB:

- `snapshots`: committed snapshot metadata and singleton-commit lifecycle
- `structural_nodes`: global structural identities and creation provenance
- `node_instances`: snapshot-bound qualified names, file locations, spans, and
  content hashes
- `edges`: committed structural relationships used as the structural baseline
- `synthetic_nodes` / `synthetic_node_instances`: non-structural navigation
  entities such as synthetic entry points; synthetic identities must remain
  collision-safe against real structural nodes

ArtifactDB:

- `callsite_pairs`: deduplicated persisted in-scope candidate caller-to-callee
  pairs
- `node_calls`: finalized callable-to-callable artifact call edges derived from
  `callsite_pairs`
- `graph_nodes` / `graph_edges`: reducer-facing graph projection rebuilt from
  CoreDB plus artifact call finalization
- `module_call_edges`, `class_call_edges`, `node_fan_stats`: derived rollups for
  reducers and reporting
- `rebuild_status`: artifact rebuild completion and diagnostics metadata
- `diff_overlay`, `diff_overlay_calls`, `diff_overlay_summary`: dirty-worktree
  overlay state layered on top of committed snapshot outputs

Overlay support model:

- patchable projections apply overlay rows directly to reducer payloads
- patchable projections may emit overlay-adjusted row sets rather than only
  mutating committed rows in place; ranking-style reducers may therefore
  materialize overlay-only rows when those rows qualify after adjustment
- metadata-only projections attach `_diff` and warning state but remain
  committed-snapshot payloads
- `overlay_available=true` only means overlay state exists for the reducer
  request; it does not by itself guarantee payload patching
- `projection_not_supported` means that behavior is intentional for the
  projection
- `projection_not_patched` should be treated as a patching gap for a projection
  that is otherwise expected to support overlay patching

Schema ownership:

- CoreDB schema/migrations live in
  `src/sciona/data_storage/core_db/schema.py`
- ArtifactDB schema/migrations live in
  `src/sciona/data_storage/artifact_db/schema.py`
- Build-time population of ArtifactDB lives in
  `src/sciona/pipelines/ops/build_artifacts.py`

## Runtime Configuration

Default config generation in `src/sciona/runtime/config/io.py` writes:

- `languages.<name>.enabled` for `python`, `typescript`, `java`, and
  `javascript`
- `discovery.exclude_globs`
- `database.timeout`
- `git.timeout`
- `logging.level`
- `logging.debug`
- `logging.structured`
- `logging.module_levels`

Current defaults in `src/sciona/runtime/config/defaults.py` disable all
languages until the user enables them in `.sciona/config.yaml`.

## Reducer Layout

- Reducer implementations live directly under `src/sciona/reducers/`
- Shared reducer logic belongs in `src/sciona/reducers/helpers/shared/`,
  `src/sciona/reducers/helpers/artifact/`, and
  `src/sciona/reducers/helpers/impl/`
- Reducer classification is metadata-driven, not directory-driven
- Reducer emission flows through `src/sciona/pipelines/ops/reducers.py`
- Reducers return structured JSON-compatible payload objects; 
- Reducer emission opens CoreDB for committed snapshot identity resolution and
  ArtifactDB for reducer-facing projections
- Reducers may receive overlay decoration when the worktree is dirty
- Relationship reducers support optional narrowing arguments to reduce payload
  size for targeted analysis; current examples include
  `module_call_graph_summary(from_module_id, to_module_id)`,
  `classifier_call_graph_summary(caller_id, callee_id)`,
  `callsite_pairs_index(identifier)`,
  `fan_summary(edge_kind, min_fan, node_kind)`, and
  `symbol_references(kind, module_id)`
- Under overlay, `fan_summary` table mode reports adjusted rankings and may
  include overlay-added nodes while preserving committed baseline counts,
  adjusted counts, deltas, and row-origin semantics
- Metrics reducers now include compact decision-surface summaries for common
  workflows:
  `call_resolution_drop_summary` for dropped-call triage and
  `overlay_projection_status_summary` for overlay trust/patchability status

## Addon API

Addon authoring, import boundaries, compatibility, and public API usage are
documented in `docs/ADDONS.md`.

Keep this guide focused on core implementation and runtime architecture.

## Testing Workflow

Baseline:

```bash
pytest -q
```

For focused validation, prefer the narrowest relevant subset.

Coverage themes that matter for structural changes:

- contract/compliance invariants;
- lexical containment validation;
- determinism and singleton committed-snapshot behavior;
- parity contract and capability manifest alignment;
- strict `CALLS` candidate gate behavior;
- reducer output stability and overlay handling;
- addon public API and import-boundary tests.
