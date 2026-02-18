# SCIONA Developer Guide

This guide consolidates the required core, contracts, and addon rules for working on SCIONA. It is intentionally brief and self-contained and is the single source of truth for contributors.

## Purpose and invariants

SCIONA builds a deterministic structural index (SCI) for a git repository. It records *what exists* and *how entities relate* for a committed snapshot only. It does **not** execute code or infer semantics.

## Requirements

Comment: SCIONA currently requires Python 3.11 or 3.12. Ensure `git` and `pip` are available on your PATH.
Comment: Python 3.13 is not supported yet because `tree_sitter_languages` has no published wheels for 3.13.

Core invariants (all must hold):
- Deterministic output for the same repo state, config, and version.
- Snapshots are committed-only and logically immutable.
- CoreDB keeps exactly one committed snapshot (latest clean-HEAD build).
- Core is read-only with respect to the target repo except `sciona init` and `sciona build` writing under `.sciona/`, `sciona init` can optionally add post-commit hook.
- Committed snapshot ids are deterministic (structural content + git metadata).
- Derived artifacts live outside SCI and never modify it.
- Public pipelines and CLI read the latest committed snapshot only.
- ArtifactDB always reflects the latest committed snapshot.
- Reducers must not expose wall-clock metadata (timestamps, UUIDs).
- No network calls during analysis or reducers.

## Repository layout and ownership boundaries

Layer mapping (no layer may reach “up” the stack):
- `src/sciona/runtime/`: paths, config parsing, logging, git plumbing, error types.
- `src/sciona/data_storage/`: CoreDB/ArtifactDB schemas and read/write helpers.
- `src/sciona/code_analysis/`: discovery, parsing, node/edge extraction, normalization.
- `src/sciona/pipelines/`: policy validation, orchestration, build lifecycle, reducer execution context.
- `src/sciona/reducers/`: deterministic payload formatting and registry.
- `src/sciona/api/`: stable public addon API surface (`sciona.api.addons`).

Internal boundaries: `sciona.api.cli`, `sciona.api.errors`.

If you change invariants, update this guide first, then align code and tests.

## Public API contract

The only stable API is `sciona.api.addons` and symbols exported from its `__all__`.

Stable namespace:
- `sciona.api.addons`

CLI implementations must depend on `sciona.api.cli` (internal boundary) only.

## CLI and pipelines

CLI entrypoint:
- `sciona.cli.main:run` (registered in `pyproject.toml`).

CLI pipeline functions (from `sciona.api.cli`, internal):
- `init`, `build`, `status`
- `init_dialog_defaults`, `init_supported_languages`, `init_apply_languages`
- `clean`, `clean_agents`
- `emit`, `list_entries`, `get_entry` (reducers)
- `identifier_for_repo`, `identifier`, `require_identifier` (resolution)

Build lifecycle (implementation in `pipelines.exec.build`):
1. Validate repo/config policy.
2. Ingest snapshot and compute structural hash.
3. Reuse baseline snapshot if structural hash matches; else commit a new snapshot.
4. Enforce a single committed snapshot in CoreDB.
5. Rebuild artifacts for the committed snapshot.

## Snapshot and dirty-worktree policy

Authoritative data is always the latest committed snapshot. If the worktree is dirty:
- Reducer payloads must not silently blend dirty changes.
- Any overlay must be explicitly labeled (e.g., `_diff`) and treated as best-effort.
- Addons and tooling must treat overlays as hints, never as authoritative truth.

Clean-worktree enforcement is scoped to tracked files in enabled languages (honors `.sciona/config.yaml` and discovery excludes).

## Parsing scope and limits

Analysis is static and source-only across all supported languages. Analyzers parse source syntax using tree-sitter without importing, executing, or evaluating code. Edges (imports/calls) are syntax-based and are best-effort; partial parses are allowed and ambiguity is omitted rather than guessed. Dynamic dispatch, decorators, reflection, dependency injection, runtime registration, and build-time code generation are not modeled.

By contract, SCIONA does not:
- Execute code, import modules, or run builds/tests.
- Perform runtime symbol resolution, dataflow analysis, or type checking.
- Guarantee complete call graphs or import resolution (edges are best-effort).
- Analyze languages outside the supported list; non-tracked files are ignored.
- Index generated artifacts unless they are committed, tracked files.
- Discovery is git-tracked files only; no directory walking.
- `.gitignore` affects tracked-file discovery when files are explicitly ignored.
- Discovery applies `discovery.exclude_globs` after hard excludes (`.git/`, `.sciona/`).
- Uncommitted changes outside tracked language files do not invalidate a snapshot.
- Partial ASTs are allowed; ambiguity is omitted, not guessed.
- Import edges are syntax hints, not full symbol resolution.
- Call graphs are derived artifacts and may be incomplete.
- Module names are derived from repo-relative paths only; packaging metadata is ignored.

## Supported languages

- Python
- TypeScript
- Java

## Data model

CoreDB (SCI):
- `snapshots`, `structural_nodes`, `node_instances`, `edges`

ArtifactDB (derived, non-authoritative):
- `node_status`, `node_calls`, `graph_nodes`, `graph_edges`
- Rollups: `module_call_edges`, `class_call_edges`, `node_fan_stats`
- Optional `diff_overlay` tables for dirty-worktree payload augmentation

## DB schema summary (tables and responsibilities)

CoreDB:
- `snapshots`: committed snapshot metadata (single authoritative snapshot).
- `structural_nodes`: stable identities for structural entities.
- `node_instances`: snapshot-specific facts (names, paths, spans, hashes).
- `edges`: structural relations within a snapshot.

ArtifactDB:
- `node_status`: per-snapshot node state (added/modified/unchanged).
- `node_calls`: derived call edges with `call_hash` from core node hashes (legacy; prefer `graph_edges`).
- `graph_nodes` / `graph_edges`: consolidated structural + call graph index. `graph_edges` includes `IMPORTS_DECLARED`, `CONTAINS`, and `CALLS`.
- `rebuild_status`: artifact rebuild lifecycle (`start` / `complete` / `failed`).
- `diff_overlay*`: best-effort dirty-worktree overlays for reducer payloads.

## Reducers

Reducers are deterministic renderers over SCI/ArtifactDB data and must be read-only.
Rules:
- Reducers share a single unified namespace.
- Registry is frozen by default; mutation is a controlled exception.
- Reducers may read source files only to enrich already-known nodes.
- Reducers must not discover new nodes or infer semantics.
- Reducer existence does not imply endorsement; CLI exposure may be restricted.

Where to add reducers:
- Implement under `src/sciona/reducers/`.
- Add deterministic output tests.

Reducer execution is mediated by `src/sciona/pipelines/reducers.py`:
- Validates diff mode (`full` or `summary`).
- Resolves identifiers against the latest committed snapshot.
- Applies diff overlays when available.

## Addons

Addons are separate products that use `sciona.api.addons`; core does not load, discover, or register them.
- Allowed: consume reducers and read CoreDB/ArtifactDB via read-only helpers.
- Forbidden: register reducers/prompts in core, mutate snapshots/artifacts, or rely on internal modules/schemas.
- Compatibility: `REQUIRES_SCIONA_PLUGIN_API` (int, string major/minor, or range). Major bump breaks API; minor bump is additive.

## Configuration and on-disk artifacts

`.sciona/config.yaml` controls language enablement and runtime settings.
Constants (filenames, schema version) are in `src/sciona/runtime/constants.py`.

Typical `.sciona/` contents:
- `sciona.db` (CoreDB)
- `sciona.artifacts.db` (ArtifactDB)
- `version.json`
- `sciona.log`

## Release process

Releases are tag-based and use `setuptools_scm` for versioning.
1. Ensure a clean working tree and passing tests.
2. Create an annotated tag on the release commit (git tag -a vX.Y.Z -m "vX.Y.Z").
3. Push the tag: `git push origin vX.Y.Z`.
4. CI builds and publishes from the tag.

## Tests

Testing focuses on invariants and boundaries:
- Public API boundary tests (`sciona.api.addons` only).
- Pipeline lifecycle and artifact rebuild behavior.
- Reducer determinism and ordering.
- Storage schema invariants.

Run tests:
```bash
pytest -q
```
