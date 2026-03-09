# SCIONA Developer Guide

This guide is operational. It explains where code lives, how the current build
path works, and how to validate changes against the codebase as it exists now.

Authoritative references:

- Normative contract: `docs/CONTRACT.md`
- Generated capabilities: `docs/CAPABILITY_MANIFEST.json`
- Executable parity contract:
  `src/sciona/code_analysis/languages/common/parity_contract.py`

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

- `src/sciona/cli/`: Typer CLI entrypoint plus `build`, `init`, `agents`,
  `hooks`, `status`, `search`, `resolve`, and `reducer` command wiring
- `src/sciona/api/`: stable public addon-facing namespace; public root exports
  only `sciona.api.addons`
- `src/sciona/runtime/`: paths, config loading, logging, git helpers, time,
  reducer metadata, addon API version contract, and shared constants
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
- `src/sciona/pipelines/diff_overlay/`: dirty-worktree overlay computation,
  sorting, patching, and summary payload generation
- `src/sciona/pipelines/reducers.py`: reducer listing and emission pipeline
- `src/sciona/reducers/`: reducer implementations; helpers shared by reducers
  live in `src/sciona/reducers/helpers/`
- `tests/`: API, code-analysis, data-storage, pipeline, reducer, and runtime
  coverage

Core dependency direction is still downward by layer, but artifact and overlay
modules are first-class parts of the current implementation and should not be
treated as optional sidecars.

## Language Adapter Architecture

Pipeline:

```text
tracked git files
  -> discovery + file snapshots
  -> builtin language analyzer
  -> AnalysisResult (nodes / edges / call_records)
  -> StructuralAssembler
  -> CoreDB committed snapshot
  -> ArtifactEngine re-analysis
  -> ArtifactDB finalized reducer-facing projections
  -> overlay support
```

Current adapter contract is `AdapterSpecV1` in
`src/sciona/code_analysis/core/extract/contracts/language_adapter.py`.

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
- JavaScript reuses the TypeScript walker, import extraction, and call
  resolution wrappers with JavaScript query surfaces
- Parser bootstrap is isolated in
  `src/sciona/code_analysis/core/extract/parsing/parser_bootstrap.py`
- Query helpers stay separate in
  `src/sciona/code_analysis/core/extract/parsing/query_helpers.py`
- Strict call candidate acceptance remains core-owned in
  `src/sciona/code_analysis/contracts/strict_call_contract.py` and
  `src/sciona/code_analysis/core/structural_assembler.py`
- Reducer-facing `CALLS`, `call_sites`, graph edges, fan stats, and rollups are
  finalized in ArtifactDB, not served directly from CoreDB `edges`

## Build Lifecycle

`src/sciona/pipelines/exec/build.py` is the current high-level build path:

1. Create snapshot metadata and compute a build fingerprint.
2. Reuse cached build results immediately when fingerprint matches and
   `force_rebuild` is false.
3. Open a CoreDB transaction and purge uncommitted snapshots.
4. Load the latest committed snapshot as the reuse baseline.
5. Run `BuildEngine` over tracked files for enabled languages.
6. Compute the structural hash and deterministic canonical snapshot id.
7. Reuse or commit the snapshot based on the structural hash decision.
8. Enforce the singleton committed-snapshot invariant and prune orphan
   structural and synthetic nodes.
9. Run artifact analysis and rebuild ArtifactDB when artifact refresh is
   enabled.
10. Persist fingerprint cache data for future fast-path reuse.

`BuildEngine` in `src/sciona/code_analysis/core/engine.py` currently owns:

- tracked/ignored path collection via git helpers;
- discovery filtering through `discovery.exclude_globs`;
- file-size, node-count, and call-identifier limits;
- analyzer dispatch and partial-parse fallback registration;
- accumulation of import and call-gate diagnostics.

`build_artifacts_for_snapshot()` in
`src/sciona/pipelines/build_artifacts.py` currently owns:

- artifact re-analysis through `ArtifactEngine`;
- `call_sites` and `node_calls` materialization;
- rebuild of reducer-facing graph edges and rollups;
- rebuild-status metadata and diagnostics persistence;
- overlay table clearing before fresh artifact population.

## Snapshot and Artifact Semantics

- CoreDB keeps exactly one committed snapshot
- Snapshot ids are canonicalized from structural hash, git commit sha, and
  source
- CoreDB is the committed structural ingestion store
- ArtifactDB is rebuilt immediately after the committed snapshot and acts as the
  reducer-facing latest-state derived query store for that committed snapshot
- Reducers are expected to consume ArtifactDB projections when they exist, while
  still using CoreDB for identifier resolution and committed structural context
- Reducer-facing `CALLS` is finalized in ArtifactDB from artifact analysis, not
  from raw analyzer output alone
- Core-side `AnalysisResult.call_records` normalization in
  `StructuralAssembler` is intentionally file-local and provisional; it exists
  for deterministic ingestion-time normalization and diagnostics, not as the
  authoritative repo-wide call graph
- Artifact call finalization resolves against repo-wide committed structural
  context and remains the authoritative source for reducer-facing `CALLS`
- `call_sites` is an artifact-layer table for accepted/dropped call outcomes and
  diagnostics
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

- `call_sites`: reducer-facing accepted/dropped callsite outcomes, diagnostics,
  artifact-only rescue provenance, and persisted dropped rows used by reporting
  classifications such as `external_likely`
- `node_calls`: finalized callable-to-callable artifact call edges
- `graph_nodes` / `graph_edges`: reducer-facing graph projection rebuilt from
  CoreDB plus artifact call finalization
- `module_call_edges`, `class_call_edges`, `node_fan_stats`: derived rollups for
  reducers and reporting
- `rebuild_status`: artifact rebuild completion and diagnostics metadata
- `diff_overlay`, `diff_overlay_calls`, `diff_overlay_summary`: dirty-worktree
  overlay state layered on top of committed snapshot outputs

Overlay support model:

- patchable projections apply overlay rows directly to reducer payloads
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
  `src/sciona/pipelines/build_artifacts.py`

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
- Shared reducer logic belongs in `src/sciona/reducers/helpers/`
- Reducer classification is metadata-driven, not directory-driven
- Reducer emission flows through `src/sciona/pipelines/reducers.py`
- Reducers return structured JSON-compatible payload objects; 
- Reducer emission opens CoreDB for committed snapshot identity resolution and
  ArtifactDB for reducer-facing projections
- Reducers may receive overlay decoration when the worktree is dirty
- Relationship reducers support optional narrowing arguments to reduce payload
  size for targeted analysis; current examples include
  `module_call_graph_summary(from_module_id, to_module_id)`,
  `classifier_call_graph_summary(caller_id, callee_id)`,
  `callsite_index(identifier, status, provenance, drop_reason)`,
  `fan_summary(edge_kind, min_fan, node_kind)`, and
  `symbol_references(kind, module_id)`
- Metrics reducers now include compact decision-surface summaries for common
  workflows:
  `call_resolution_drop_summary` for dropped-call triage and
  `overlay_projection_status_summary` for overlay trust/patchability status

## Addon API

Stable public addon surface is `sciona.api.addons`.

Public exports:

- `PLUGIN_API_VERSION`, `PLUGIN_API_MAJOR`, `PLUGIN_API_MINOR`
- `list_entries(...)`
- `emit(...)`
- `open_core_readonly(...)`, `open_artifact_readonly(...)`
- `core_readonly(...)`, `artifact_readonly(...)`

Boundary rules enforced by tests:

- the public root namespace is `sciona.api`, which exposes only `addons`
- addon code under `addons/` must import SCIONA through `sciona.api.addons` or
  `sciona.addons...` prefixes
- addon-facing database helpers are read-only wrappers around connection
  helpers and repo-root resolution

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
