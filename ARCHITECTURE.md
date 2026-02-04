# SCIONA Architecture (1.0)

**Normative document.**
All other documents defer to `ARCHITECTURE.md` for invariants and data-flow rules.

This document defines runtime boundaries and data flow for SCIONA 1.0.

---

## Purpose

SCIONA is a deterministic structural indexing tool. It records what exists in
code (nodes), how entities relate (edges), and which snapshot the facts came
from. It does not interpret intent or behavior.

Derived tooling (prompts) may consume the index but must not feed data back into
it.

---

## Core invariants

- Structural truth only. SCI contains syntactic structure, not intent.
- Deterministic output for the same repo state, config, and version.
- Snapshots are committed-only and immutable at the logical layer.
- Derived artifacts live outside SCI and never modify it.
- Public pipelines and CLI surfaces read the **latest committed snapshot only**.
- ArtifactDB always reflects the **latest committed snapshot**.
- Continuity is computed from history but stored only for latest snapshot nodes.
- Best-effort parsing is allowed; ambiguity is omitted, not guessed.

---

## Data model (high level)

### Core DB (SCI)

- `snapshots`: snapshot_id, created_at, source, is_committed, structural_hash, git metadata
- `structural_nodes`: stable identity (structural_id, type, language)
- `node_instances`: snapshot-specific facts (qualified_name, file_path, lines, content_hash)
- `edges`: structural relations within a snapshot

### Artifact DB (derived)

- `node_status`: per-snapshot node state (added/modified/unchanged)
- `node_calls`: derived call edges with `call_hash`
- `graph_nodes` / `graph_edges`: combined graph index (structural + calls)
- `node_continuity`: continuity metrics computed from all committed snapshots,
  stored for latest snapshot nodes only
- Rollups: `module_call_edges`, `class_call_edges`, `node_fan_stats`

Artifacts are rebuilt for the **latest committed snapshot** and are not part of SCI.

---

## Layer boundaries

### runtime
- Paths, config, logging, and errors (`runtime/*`)
- LLM adapter + providers (`runtime/llm/*`)
- Git backend (`runtime/git.py`)
- No persistence logic

### data_storage
- Connection helpers, schema, and DB operations (`data_storage/*`)
- Artifact maintenance helpers live under `data_storage/artifact_db/`
- No policy decisions or orchestration

### code_analysis
- File discovery and parsing
- Node/edge extraction and normalization
- Snapshot ingest mechanics (no DB ownership)
- Shared AST and snapshot utilities live under `core/code_analysis/tools/`

### pipelines
- Policy and validation (`pipelines.policy`)
- Orchestration (`pipelines.exec`)
- Build + artifact refresh
- Prompt compilation + prompt answering (LLM optional)

### reducers / prompts
- Deterministic payload formatting over SCI/Artifact data
- Prompt compilation using reducer outputs
- No mutation or persistence
- Reducer payload emission is centralized in `pipelines.reducers.emit`.
- Reducers live under `core/reducers/` with semantic folders:
  - `structural/` (DB-derived, non-inferential structure)
  - `summaries/` (lossy compression for LLM use)
  - `composites/` (curated multi-surface orientation)
  - `baseline/` (control/baseline reducers)
  - `helpers/` (shared utilities; not reducers)
- Reducer catalog lives in `REDUCERS.md`
- Identifier resolution for prompts/reducers is centralized in `core/pipelines/resolve.py` and returns best-fit candidates on ambiguity/missing matches.

### addons
- Addon architecture and contracts live in `ADDONS.md`
- Addons may read core databases via core data_storage helpers; they must not write.
- Addons may consume core reducers or prompt compilation services when helpful.
- Addons do not define reducers; reducers are core-owned.
- Addon registration uses the minimal registry interface in `runtime/addon_api.py`
  to avoid import cycles.

### Interfaces
- Thin adapters over pipelines
- Core CLI exposes core pipeline surfaces only.
- Prompt/reducer registries are frozen during startup
- Resolver/search surfaces provide identifier resolution and ranked symbol lookup (read-only).
- CLI exposes `resolve` (exact/ambiguous) and `search` (ranked candidates) as separate read-only surfaces.


---

## Runtime behavior

### Build lifecycle

1. Validate repo and config against policy requirements.
2. Ingest snapshot and compute structural hash.
3. Reuse latest snapshot if identical; otherwise commit a new snapshot.
4. Rotate committed snapshots per retention policy.
5. Rebuild artifacts for the latest committed snapshot (node status, call artifacts, graph index, continuity).

No ephemeral snapshots are exposed. Uncommitted snapshots are internal only.

### Parsing scope

- Discovery is driven by git-tracked files only (no directory walking).
- `.gitignore` does not affect tracked-file discovery.
- Discovery applies `discovery.exclude_globs` after hard excludes (`.git/`, `.sciona/`).
- Partial ASTs are allowed.
- Import edges are syntax-based hints, not full symbol resolution.
- Call graphs are derived artifacts and may be incomplete.
- Module names are derived from repo-relative paths only; packaging metadata is ignored.

### Historical bootstrap

When no committed snapshots exist, SCIONA can seed history by replaying a
bounded window of past commits (controlled by config). This history is used only
for continuity calculations; all outputs still target the latest committed snapshot.

---

## Determinism

SCIONA must not use network calls during analysis or reducers. Reducers must
produce stable ordering and deterministic text/JSON output.

---

## Supported languages (1.0)

- Python
- TypeScript
- Java

Other languages are out of scope for 1.0.
