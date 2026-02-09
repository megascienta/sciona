# SCIONA Contracts (1.0)

This document defines binding behavioral contracts for contributors, addons,
reducers, and tooling.

---

## Snapshot policy (binding)

Authoritative rules are defined in `ARCHITECTURE.md` (Core invariants and Runtime
behavior). This contract binds all parties to those rules and adds enforcement
expectations:

- Pipelines and CLI must enforce clean-worktree policy and clearly warn when
  operating on a dirty worktree.
- Reducer payloads must not silently blend dirty changes; any overlay must be
  explicitly labeled (e.g., `_diff`) as best-effort and non-authoritative.
- Addons and tooling must treat overlays as hints, not truth, and must not
  persist overlay content as authoritative data.

---

## Public API contract

SCIONA exposes a stable public API via `sciona.api` (and re-exports in
`sciona.__init__`). The public surface is the set of modules under `sciona.api`
and their `__all__` exports. The preferred entrypoint for user-facing code is
`sciona.api.user`.

- `sciona.api.user` for user-facing library operations (preferred)
- `sciona.api.addons` for addon/plugin operations
- `sciona.api.reducers` for reducer registry and rendering helpers
- `sciona.api.repo` for repo lifecycle (init/build/status/clean) helpers
- `sciona.api.resolve` for identifier resolution helpers
- `sciona.api.runtime` for runtime wiring (paths, config, logging)
- `sciona.api.storage` for read-only CoreDB/ArtifactDB access
- `sciona.api.errors` for public error types

Only symbols exported from these namespaces are considered stable and supported.
All other modules and symbols are internal and may change without notice.

Notes:
- CLI implementations must depend on `sciona.api.*` only.

---

## Addon contract (binding)

This contract applies to all addon products. See `ADDONSDEVGUIDE.md` for the
standalone addon developer manual.

- Addons must consume core via `sciona.api.*` only.
- Addons must not register reducers into core.
- Addons must not mutate snapshots or rely on internal storage schemas.
- Addons may access CoreDB/ArtifactDB in **read-only** mode via
  `sciona.api.storage` or `sciona.api.addons` helpers.

---

## Reducer contract (binding)

Reducer invariants are defined in `ARCHITECTURE.md`. This contract adds the
following operational constraints:

- Reducers share a single unified namespace; there is no internal-only class.
- The reducer registry is frozen by default; mutation is a controlled exception.
- Reducer existence does not imply endorsement; CLI exposure may be restricted.
- Reducers may read source files only to enrich already-known nodes (signatures,
  spans, decorators). Reducers must not discover new nodes or infer semantics.

---

## Edge contract

Edge and node type semantics are defined in `ARCHITECTURE.md`. This contract
binds contributors to:

- Avoid introducing new node/edge types without updating `ARCHITECTURE.md` and
  the relevant tests.
- Avoid changing existing semantics without updating `ARCHITECTURE.md` and all
  dependent reducers.

---

## Ingest contract

Ingestor emission rules are defined in `ARCHITECTURE.md`. Any change to ingest
behavior must update `ARCHITECTURE.md` first, then adjust ingestors and tests to
match.

---

## Artifact contract

Artifacts are derived and stored in ArtifactDB per `ARCHITECTURE.md`. They are
not authoritative structural truth. Artifact rebuild helpers live under
`data_storage/artifact_db/`.

- `node_status` is rebuilt for the latest committed snapshot.
- `node_calls.call_hash` is the node content hash from the core snapshot.
- `graph_nodes`/`graph_edges` are rebuilt from core edges and node_calls.
- Artifact rebuild lifecycle is tracked in `rebuild_status` (`start` / `complete` / `failed`).

These rollups are derived from the committed snapshot and are used by reducers
for efficient summaries:
- `module_call_edges`
- `class_call_edges`
- `node_fan_stats`
