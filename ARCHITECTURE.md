# SCIONA Architecture (1.0)

**Normative document.**
All other documents defer to `ARCHITECTURE.md` for invariants and data-flow rules.

This document defines runtime boundaries and data flow for SCIONA 1.0.

---

## Purpose

SCIONA is a deterministic structural indexing tool. It records what exists in
code (nodes), how entities relate (edges), and which snapshot the facts came
from. It does not interpret intent or behavior.

Derived tooling (addons) may consume the index but must not feed data back into
it.

---

## Core invariants

- Structural truth only. SCI contains syntactic structure, not intent.
- Deterministic output for the same repo state, config, and version.
- Snapshots are committed-only and immutable at the logical layer.
- CoreDB keeps exactly one committed snapshot (the latest clean-HEAD build).
- SCIONA is read-only with respect to the target repo during normal operation.
  Repo-root mutations are limited to explicit, opt-in setup steps (e.g.,
  `sciona init` creating/populating `.sciona/` and optional post-commit hook
  installation). Outside setup, only `sciona build` may write under `.sciona/`.
- Committed snapshot ids are deterministic and derived from structural content
  and git commit metadata; ingest-time ids are internal only.
- Derived artifacts live outside SCI and never modify it.
- Public pipelines and CLI surfaces read the **latest committed snapshot only**.
- ArtifactDB always reflects the **latest committed snapshot**.
- Best-effort parsing is allowed; ambiguity is omitted, not guessed.
- Reducers must not expose timestamps, UUIDs, or other wall-clock metadata.

---

## Data model (high level)

### Core DB (SCI)

- `snapshots`: snapshot_id, created_at, source, is_committed, structural_hash, git metadata
  - `created_at` is internal metadata; "latest snapshot" selection uses commit
    metadata, not wall-clock time.
- `structural_nodes`: stable identity (structural_id, type, language)
- `node_instances`: snapshot-specific facts (qualified_name, file_path, lines, content_hash)
- `edges`: structural relations within a snapshot

### Artifact DB (derived)

- `node_status`: per-snapshot node state (added/modified/unchanged)
- `node_calls`: derived call edges with `call_hash`
- `graph_nodes` / `graph_edges`: combined graph index (structural + calls)
- Rollups: `module_call_edges`, `class_call_edges`, `node_fan_stats`
- `diff_overlay`: dirty-worktree overlay rows used to augment reducer payloads
- `diff_overlay_calls`: dirty-worktree call-edge overlays
- `diff_overlay_summary`: dirty-worktree overlay summary stats

Artifacts are rebuilt for the **latest committed snapshot** and are not part of SCI.

---

## Layer boundaries

### runtime
- Paths, config parsing, logging, and errors (`runtime/*`)
- Git backend (`runtime/git.py`)
- Infrastructure only (no pipeline policy/domain models, no reducer assembly, no persistence/domain logic)

### data_storage
- Connection helpers, schema, and DB operations (`data_storage/*`)
- Artifact maintenance helpers live under `data_storage/artifact_db/`
- No policy decisions or orchestration

#### data_storage API map (read/write split)

- CoreDB
  - `data_storage/core_db/read_ops.py`: snapshot lookup/validation, node/edge queries, structural-hash inputs
  - `data_storage/core_db/write_ops.py`: inserts/upserts, snapshot lifecycle cleanup, pruning
  - `data_storage/core_db/errors.py`: snapshot validation errors
- ArtifactDB
  - `data_storage/artifact_db/read_status.py`: node status and rebuild-status reads
  - `data_storage/artifact_db/write_index.py`: node status + node call writes, rebuild-status writes
  - `data_storage/artifact_db/write_graph.py`: graph index writes

### code_analysis
- File discovery and parsing
- Node/edge extraction and normalization
- Snapshot ingest mechanics (no DB ownership)
- Shared AST and snapshot utilities live under `code_analysis/tools/`

### pipelines
- Policy and validation (`pipelines.policy`)
- Domain models (`pipelines.domain`)
- Orchestration (`pipelines.exec`)
- Build + artifact refresh
- Owns reducer execution context (opens DB connections and passes read handles to reducers)

### reducers
- Deterministic payload formatting over SCI/Artifact data
- No mutation or persistence
- No path discovery or connection ownership (read handles are supplied by pipelines)
- Reducer payload emission is centralized in `pipelines.reducers.emit`.
- Reducers live under `reducers/` with semantic folders:
  - `structural/` (DB-derived, non-inferential structure)
  - `summaries/` (lossy compression for LLM use)
  - `composites/` (curated multi-surface orientation)
  - `baseline/` (control/baseline reducers)
  - `helpers/` (shared utilities; not reducers)
- Reducer catalog lives in `REDUCERS.md`
- Identifier resolution for reducers is centralized in `pipelines/resolve.py` and returns best-fit candidates on ambiguity/missing matches.

### addons
- Addon/plugin contracts live in `CONTRACTS.md` ("Addon plugin contract")
- Core does not load addons. Addons are separate products that consume core via
  the public API (`sciona.api.*`).
- Addons may consume core reducer emission through `sciona.api.addons`.
- Addons must not register reducers or prompts into core.
- Addons may access CoreDB/ArtifactDB via **read-only** storage helpers
  (`sciona.api.storage`), but should prefer reducers as the primary contract.

### Interfaces
- Thin adapters over pipelines
- Core CLI exposes core pipeline surfaces only.
- Reducer registry is frozen during startup
- Resolver/search surfaces provide identifier resolution and ranked symbol lookup (read-only).
- CLI exposes `resolve` (exact/ambiguous) and `search` (ranked candidates) as separate read-only surfaces.


---

## Runtime behavior

### Build lifecycle

1. Validate repo and config against policy requirements.
2. Ingest snapshot and compute structural hash.
3. Reuse the existing committed snapshot if identical; otherwise commit a new snapshot.
4. Enforce a single committed snapshot in CoreDB.
5. Commit CoreDB transaction.
6. Rebuild artifacts for the committed snapshot (node status, call artifacts, graph index).
7. Record artifact rebuild status (`start`/`complete`/`failed`) in ArtifactDB.

No ephemeral snapshots are exposed. Uncommitted snapshots are internal only.

### Dirty-worktree overlays

When the worktree is dirty, pipelines may compute a best-effort `diff_overlay`
in ArtifactDB and apply it to reducer payloads. The overlay never modifies
CoreDB or ArtifactDB structural truth; it only augments payloads at render time.
The `_diff` payload (v2) includes `overlay_available`/`overlay_reason`, grouped
`changes` (nodes/edges/calls), summary stats, a deterministic `top_changed` list,
and declarative scope metadata (`diff_scope`, `scope_exclusions`). When the
snapshot commit diverges from `HEAD`, overlays use the merge-base as the baseline
and emit a warning. Submodule paths are ignored with a warning. If the worktree
is dirty and no overlay can be produced, reducers attach `_diff` with
`overlay_available=false` and emit a top-level `snapshot_warning`.

### Parsing scope

- Discovery is driven by git-tracked files only (no directory walking).
- `.gitignore` affects tracked-file discovery when files are explicitly ignored.
- Discovery applies `discovery.exclude_globs` after hard excludes (`.git/`, `.sciona/`).
- Clean-worktree enforcement is scoped to tracked files in enabled languages after excludes/ignores.
- Uncommitted changes outside tracked language files do not invalidate a snapshot.
- Partial ASTs are allowed.
- Import edges are syntax-based hints, not full symbol resolution.
- Call graphs are derived artifacts and may be incomplete.
- Module names are derived from repo-relative paths only; packaging metadata is ignored.

## Determinism

SCIONA must not use network calls during analysis or reducers. Reducers must
produce stable ordering and deterministic text/JSON output.

---

## Supported languages (1.0)

- Python
- TypeScript
- Java

Other languages are out of scope for 1.0.
