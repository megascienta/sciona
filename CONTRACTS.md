# SCIONA Contracts (1.0)

This document defines binding contracts for contributors, addons, reducers, and tooling,
including ingestion, edges, reducers, and CLI usage in SCIONA 1.0. Prompt tooling is owned
by the prompts addon.

---

## Snapshot policy (global contract)

Applies to core, reducers, addons, and CLI.

- All public pipelines/CLI operate on the **latest committed snapshot only**.
- CoreDB must contain exactly one committed snapshot after a successful build.
- ArtifactDB always reflects the **latest committed snapshot** (see Artifact DB
  definition in `ARCHITECTURE.md`).
- Build requires a **clean worktree** for tracked language sources in scope
  (enabled languages after excludes/ignores). Untracked files do not block builds.
- Read-only commands may proceed on a dirty worktree but must warn that outputs
  reflect the last committed snapshot. Pipelines may append a best-effort
  `diff_overlay` to reducer payloads when the worktree is dirty. The overlay may
  patch structural fields and include call-edge diffs and summary stats, but is
  non-authoritative. `_diff` includes baseline metadata (snapshot/head/merge-base),
  patch coverage, and warnings.

---

## Public API contract

SCIONA exposes a **stable public API** via `sciona.api` (and re-exports in
`sciona.__init__`). The public surface is the set of modules under `sciona.api`
and their `__all__` exports. The **preferred entrypoint** for user-facing code
is `sciona.api.user`; other namespaces are advanced surfaces used by tooling.

- `sciona.api.user` for user-facing library operations (preferred)
- `sciona.api.addons` for addon/plugin operations
- `sciona.api.reducers` for reducer registry and rendering helpers
- `sciona.api.repo` for repo lifecycle (init/build/status/clean) helpers
- `sciona.api.resolve` for identifier resolution helpers
- `sciona.api.runtime` for runtime wiring (paths, config, logging)
- `sciona.api.storage` for read-only CoreDB/ArtifactDB access
- `sciona.api.errors` for public error types

Only symbols exported from these namespaces are considered stable and supported.
All other modules and symbols are **internal** and may change without notice.
CLI implementations must depend on `sciona.api.*` only.

See each module’s `__all__` for the canonical list.

Notes:
- Registry mutation helpers (`freeze_registry`, `mutable_registry`) are intentionally
  not part of the public API surface.
- Addons can enumerate core reducers via `sciona.api.addons.list_entries` (see `REDUCERS.md` for the canonical list).
- Addons may open CoreDB/ArtifactDB in **read-only** mode via `sciona.api.storage` or `sciona.api.addons` helpers.
- Prompt tooling is provided by `sciona.addons.prompts` and is not part of core.
- Addon auto-loading is opt-in. Core CLI only loads addon entry points when
  `SCIONA_ENABLE_ADDONS=1` is set.

---

## Edge contract

### Node types

- `module`: file or compilation unit namespace
- `class`: class/type declaration
- `function`: top-level callable
- `method`: callable defined as a class member

### Edge types

#### CONTAINS

Meaning: lexical containment.

Emit when:
- module contains class
- module contains function

#### DEFINES_METHOD

Meaning: class defines a method.

Emit when:
- class contains method definitions

Notes:
- Do not emit module CONTAINS method for class methods.

#### IMPORTS_DECLARED

Meaning: explicit import statement (syntax-only, best-effort).

Emit when:
- Python `import` / `from ... import`
- TypeScript `import` syntax
- Java `import` / `import static` syntax

Notes:
- Import edges may target external modules.
- Unresolved or ambiguous imports may be omitted.

### Non-goals (SCI)

- CALLS / CALLERS
- Symbol resolution
- Type inference
- Runtime behavior
- Cross-language linkage

---

## Ingest contract

Every ingestor must emit, per file:

Nodes:
- one `module`
- zero or more `class`
- zero or more `function`
- zero or more `method`

Edges:
- module CONTAINS class
- module CONTAINS function
- class DEFINES_METHOD method
- module IMPORTS_DECLARED module (best-effort)

Failure handling:
- On parse failure: still emit the module node.
- Partial ASTs are allowed and recorded.

Supported languages (1.0): Python, TypeScript, Java.

Discovery:
- Core discovery is driven by git-tracked files only.
- `.gitignore` affects tracked-file discovery when files are explicitly ignored.

---

## Artifact contract

Artifacts are derived and stored in ArtifactDB.
Artifact rebuild helpers live under `data_storage/artifact_db/`.

- `node_status` is rebuilt for the latest committed snapshot.
- `node_calls.call_hash` is the node content hash from the core snapshot.
- `graph_nodes`/`graph_edges` are rebuilt from core edges and node_calls.
- Artifact rebuild lifecycle is tracked in `rebuild_status` (`start` / `complete` / `failed`).

Artifacts are not authoritative structural truth.
ArtifactDB is always scoped to the latest committed snapshot.
CoreDB and ArtifactDB are not cross-DB atomic; artifacts are rebuilt after core commit.

### Graph rollups (ArtifactDB)

The artifact rebuild step may also materialize derived rollups for the graph:

- `module_call_edges`: module-level call aggregation derived from `CALLS` edges
- `class_call_edges`: class-level call aggregation derived from `CALLS` edges
- `node_fan_stats`: per-node fan-in/fan-out counts by `edge_kind`

These rollups are derived from the same committed snapshot as `graph_edges` and
are used by reducers for efficient summaries. They do not add new edges or semantics.

---

## Reducer contract

Reducers are deterministic formatters of SCI/Artifact data, registered in a single
capability registry.

Rules:
- Reducers must not mutate storage.
- Reducers must not call external services.
- Output must be deterministic and ordered.
- Reducers return JSON payloads only.
- Reducers operate on the **latest committed snapshot only**.
- Pipelines may append a `_diff` overlay to reducer payloads when the worktree
  is dirty; this overlay is best-effort and non-authoritative, and may patch
  structural fields and include call-edge diffs and summary stats. Overlays
  include baseline metadata (snapshot/head/merge-base), patch coverage, and warnings,
  use the merge-base between the snapshot commit and `HEAD` when they diverge,
  and ignore submodule paths with a warning.
- Reducers must not own DB path resolution or connection lifecycle; pipelines provide read context.
- The reducer registry is frozen by default.
- Reducers share a single unified namespace; there is no internal-only reducer class.
- The reducer registry is a capability surface; reducer existence does not imply endorsement.
- Some reducers may be hidden from CLI surfaces (e.g., control/baseline surfaces).
- Reducers must treat SCI/Artifact DBs as the authoritative source of truth.
- Source files may be read only to enrich already-known nodes (signatures, parameters, decorators, doc spans).
- Reducers must never discover new nodes, infer new relationships, or perform semantic analysis.
- Reducers must declare metadata with exactly one placeholder (used by prompt tooling).
- The canonical reducer inventory for prompt addon authors is documented in `REDUCERS.md`.

Graph traversal surfaces must use the artifact graph (`graph_nodes`/`graph_edges`).
Core structural edges are not used for traversal in public surfaces.

Reducer categories are semantic only and live under:
- `reducers/structural` (DB-derived, non-inferential structure)
- `reducers/summaries` (lossy compression)
- `reducers/composites` (curated orientation)
- `reducers/baseline` (control/baseline surfaces)
- `reducers/helpers` (shared utilities, not reducers)

### Public reducer tiers (frozen)

Structural spine (core, required by tooling):
- structural_index
- module_overview
- callable_overview
- call_graph
- class_overview
- class_inheritance

Baseline / control (public, non-core):
- concatenated_source

Derived / optional (public, non-core):
- fan_summary
- hotspot_summary
- class_call_graph
- module_call_graph
- callsite_index
- importers_index

Structural optional (public, non-core):
- symbol_lookup
- symbol_references
- file_outline
- module_file_map
- dependency_edges
- import_references

Prompt tooling should prefer structural spine reducers. Baseline and derived reducers
are allowed for experiments or addon-specific prompts.

Note:
- `concatenated_source` returns JSON with per-file entries and includes only snapshot-tracked files
  (from `node_instances`); it does not scan the filesystem.

### Ordering rules

Reducers must return stable ordering. Current guarantees:

- `structural_index`:
  - modules.entries sorted by module_qualified_name
  - files.entries sorted by path
  - classes.entries sorted by qualified_name
  - classes.by_module/functions.by_module/methods.by_module sorted by (-count, key)
  - imports.edges sorted by (from_module_qualified_name, to_module_qualified_name)
  - import_cycles sorted lexicographically
- `module_overview`:
  - files sorted by path
  - classes/functions/methods sorted by qualified_name

---

## Prompt contract

Prompt tooling is owned by the prompts addon (`sciona.addons.prompts`). See the
addon documentation for prompt registry and compilation contracts.

---

## Addon plugin contract

- Addons are discovered from Python entry points in group `sciona.addons`.
- Addons may only register CLI commands through `runtime/addon_api.Registry.register_cli`.
- Core auto-attaches installed addon CLI commands to the `sciona` CLI.
- Addons may call reducer emission through `sciona.api.addons`. Prompt compilation is provided
  by the prompts addon.
- `sciona.api.addons` exports plugin API version constants (`PLUGIN_API_VERSION`,
  `PLUGIN_API_MAJOR`, `PLUGIN_API_MINOR`).
- Addons may declare `REQUIRES_SCIONA_PLUGIN_API` (e.g., `">=1,<2"`); incompatible
  addons are skipped during load.
- Addons must not register reducers or prompts into core registries.

---

## Module naming contract

- Module identifiers are derived from repo-relative paths only.
- The repo root folder name is the top-level prefix.
- Language packaging metadata (pyproject package-dir, npm package name, etc.) is ignored.
- Python `__init__.py` files collapse to their package path.
- Other languages use the dotted file path minus the extension.
- Directory modules are synthesized for any folder containing tracked files.

Note: packaging metadata may be used for best-effort import normalization, but
never for module identifiers.

---

## Config contract

Public config/runtime surfaces:
- `runtime.config`: typed config loading (`load_sciona_config`, `load_runtime_config`,
  `load_language_settings`, `load_logging_settings`)
- `runtime.config.io`: config file read/write helpers used by init workflows
- `runtime.paths`: repository and state paths (`get_repo_root`, `get_sciona_dir`,
  `get_db_path`, `get_artifact_db_path`, `get_config_path`, ...)

All user-configurable core settings live in `.sciona/config.yaml`. Prompt addon
settings (including LLM config) live under `.sciona/prompts/`.
