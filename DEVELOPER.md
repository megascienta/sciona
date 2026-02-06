# SCIONA Developer Guide

This guide is for contributors and maintainers. It consolidates architecture,
contracts, and reducer inventory.

## Architecture overview

SCIONA builds a deterministic structural code index (SCI) from git-tracked
source files. It stores a single latest committed snapshot in CoreDB and
derived artifacts in ArtifactDB.

## Build lifecycle

1. Validate repo and config against policy requirements.
2. Ingest a snapshot and compute structural hash.
3. Reuse existing committed snapshot if identical; otherwise commit a new snapshot.
4. Enforce a single committed snapshot in CoreDB.
5. Commit CoreDB transaction.
6. Rebuild artifacts for the committed snapshot (node status, call artifacts, graph index).
7. Record artifact rebuild status (`start`/`complete`/`failed`) in ArtifactDB.

## CoreDB vs ArtifactDB

- CoreDB stores structural truth for committed snapshots.
- ArtifactDB stores derived artifacts (graphs, call edges, overlays).
- Reducers read from CoreDB/ArtifactDB only; they never mutate storage.

## Reducer contract (binding)

- Reducers must not mutate storage.
- Reducers must not call external services.
- Output must be deterministic and ordered.
- Reducers return JSON payloads only.
- Reducers operate on the latest committed snapshot only.
- Reducers must not own DB path resolution or connection lifecycle.
- Reducers never discover new nodes or infer relationships.

### Dirty-worktree overlays

Pipelines may append a best-effort `_diff` overlay to reducer payloads when the
worktree is dirty. `_diff` includes baseline metadata (snapshot/head/merge-base),
patch coverage, and warnings. Overlays are non-authoritative.

## Prompt contract

- Prompt compilation is deterministic.
- Prompts use reducer payloads as evidence.
- Prompt templates and registry live in `.sciona/prompts`.

## Reducer inventory

Structural spine (core, required by tooling):
- structural_index
- module_overview
- callable_overview
- call_graph
- class_overview
- class_inheritance

Baseline / control (public, non-core):
- callable_source
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

Notes:
- callable_overview accepts function_id, method_id, or callable_id.
- module_overview accepts module_id or resolves from callable/function/method/class id.
- class_overview accepts class_id or resolves from method_id.

## Public API boundaries

The public surface is `sciona.api.*` and their `__all__` exports. All other
modules are internal and may change without notice. CLI must depend on
`sciona.api.*` only.

## Logging and errors

- Use `runtime.logging.get_logger` for logging.
- Use `runtime.errors.ScionaError` subclasses for user-facing failures.

## Tests

```bash
pytest -q
```

## Hooks

Optional post-commit hook support:
- sciona hooks install|status|remove
- sciona init --post-commit-hook

## Documentation

Docs live in root:
- README.md (simple user guide)
- USERGUIDE.md (expectations + limitations)
- DEVELOPER.md (this file)
- ADDONS.md (addons guide)
