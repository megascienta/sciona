# SCIONA Contracts (1.0)

This document defines binding contracts for contributors, addons, prompts, and tooling.
This document defines the external contracts for ingestion, edges, reducers,
prompts, and CLI usage in SCIONA 1.0.

---

## Snapshot policy (global contract)

Applies to core, reducers, prompts, addons, and CLI.

- All public pipelines/CLI operate on the **latest committed snapshot only**.
- ArtifactDB always reflects the **latest committed snapshot** (see Artifact DB
  definition in `ARCHITECTURE.md`).
- History is used only to compute continuity metrics stored for latest snapshot nodes
  (see continuity rules in `ARCHITECTURE.md`).
- Build/rebuild require a **clean worktree** for tracked language sources.
- Read-only commands may proceed on a dirty worktree but must warn that outputs
  reflect the last committed snapshot.

---

## Public API contract

SCIONA exposes a **stable public API** via `sciona.api` (and re-exports in
`sciona.__init__`). Facade modules `sciona.runtime.api` and `sciona.reducers.api`
are also part of the public API surface. Only symbols exported from these
modules are considered stable and supported. All other modules and symbols are
**internal** and may change without notice.

The public API surface includes:
- CLI entrypoints and command registration
- Repo lifecycle pipeline helpers
- Reducer access helpers
- Identifier resolution helpers
- Addon registry integration points
- Read-only DB connection helpers

See `sciona.api` for the canonical list.

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
- `.gitignore` does not affect tracked-file discovery.

---

## Artifact contract

Artifacts are derived and stored in ArtifactDB.
Artifact rebuild helpers live under `data_storage/artifact_db/`.

- `node_status` is rebuilt for the latest committed snapshot.
- `node_calls.call_hash` is the node content hash from the core snapshot.
- `graph_nodes`/`graph_edges` are rebuilt from core edges and node_calls.
- `node_continuity` is recomputed using all committed snapshots but stored only
  for nodes in the latest committed snapshot.

Artifacts are not authoritative structural truth.
ArtifactDB is always scoped to the latest committed snapshot.

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
- Reducers operate on the **latest committed snapshot only**.
- The reducer registry is frozen by default.
- Reducers share a single unified namespace; there is no internal-only reducer class.
- The reducer registry is a capability surface; reducer existence does not imply endorsement.
- Some reducers may be hidden from CLI surfaces (e.g., control/baseline surfaces).
- Reducers must treat SCI/Artifact DBs as the authoritative source of truth.
- Source files may be read only to enrich already-known nodes (signatures, parameters, decorators, doc spans).
- Reducers must never discover new nodes, infer new relationships, or perform semantic analysis.
- Reducers must declare metadata with exactly one placeholder (used by prompt compilation).
- The canonical reducer inventory for prompt authors is documented in `REDUCERS.md`.

Graph traversal surfaces must use the artifact graph (`graph_nodes`/`graph_edges`).
Core structural edges are not used for traversal in public surfaces.

Reducer categories are semantic only and live under:
- `core/reducers/structural` (DB-derived, non-inferential structure)
- `core/reducers/summaries` (lossy compression)
- `core/reducers/composites` (curated orientation)
- `core/reducers/baseline` (control/baseline surfaces)
- `core/reducers/helpers` (shared utilities, not reducers)

### Public reducer tiers (frozen)

Structural spine (core, required by tooling):
- structural_index
- module_overview
- callable_overview
- call_graph
- class_overview
- class_method_list
- class_inheritance

Baseline / control (public, non-core):
- concatenated_source

Derived / optional (public, non-core):
- fan_summary
- hotspot_summary
- class_call_graph
- module_call_graph
- confidence_summary
- continuity_summary
- callsite_index

Structural optional (public, non-core):
- symbol_lookup
- dependency_edges
- import_references

Prompts should prefer structural spine reducers. Baseline and derived reducers
are allowed for experiments or addon-specific prompts.

### Ordering rules

Reducers must return stable ordering. Current guarantees:

- `structural_index`:
  - modules.entries sorted by module_id
  - files.entries sorted by path
  - classes.entries sorted by qualified_name
  - classes.by_module/functions.by_module/methods.by_module sorted by (-count, key)
  - imports.edges sorted by (from_module_id, to_module_id)
  - import_cycles sorted lexicographically
- `module_overview`:
  - files sorted by path
  - classes/functions/methods sorted by qualified_name

---

## Prompt contract

- Prompts are derived tooling and never feed back into SCI.
- Prompt registry is YAML under `.sciona/prompts/registry.yaml`; core seeds bundled prompts at init.
- Addons may provide prompt entries and templates via addon registries.
- Templates must use only registered placeholders.
- Compiler enforces placeholder bijection.
- Reducer placeholders are declared in `REDUCER_META.placeholders` (see `REDUCERS.md`).
- Prompt registries must declare every reducer-required argument in
  `required_args`/`optional_args`/`default_args`; missing reducer-required args
  are rejected during registry validation.
- Prompt registries may declare optional/default args not required by reducers;
  these emit a warning to help keep prompt interfaces tight.
- Compiled prompt header includes PROMPT and SNAPSHOT.
- Prompt usefulness/certification is evaluated at the prompt level, not the reducer level.
- Prompt compilation/answering uses the latest committed snapshot only; any other snapshot id is rejected.
- JSON prompt payloads include the full prompt text plus split `prompt_header`,
  `prompt_body`, `instructions`, `evidence`, and `resolved_arg_map` fields (when present)
  for machine parsing and identifier validation.
- CLI prompt output is human-readable by default; `--json` emits the JSON payload.
- Core CLI exposes prompts from the repo registry only; addon prompts are not available via CLI.
- CLI reducer output is machine-readable JSON by default.
- Addon registration uses `runtime/addon_api.py` and must not import `sciona.api` at module import time.

Prompt answering (CLI `--answer`) compiles the prompt and sends it to the
configured LLM; no artifact is persisted.

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

Public config interface (`pipelines.config.public`):
- `load_sciona_config`
- `load_runtime_config`
- `load_language_settings`
- `load_llm_settings`
- `load_logging_settings`

All user-configurable core settings live in `.sciona/config.yaml`. LLM settings are
top-level (`llm:`).
