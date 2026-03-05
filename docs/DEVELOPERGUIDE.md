# SCIONA Developer Guide

This guide is operational. It explains where code lives, how to work safely, and
how to validate changes.

Authoritative references:

- Normative contract: `docs/CONTRACT.md`
- Generated capabilities: `docs/CAPABILITY_MANIFEST.json`
- Executable parity contract:
  `src/sciona/code_analysis/languages/common/parity_contract.py`

If this guide conflicts with `CONTRACT.md`, the contract wins.

## Scope

Use this document for:

- repository boundaries and ownership;
- extraction architecture at implementation level;
- addon API entry points;
- required test workflow.

Do not use this document to redefine structural semantics.

## Runtime

- Python: 3.11 or 3.12
- `tree_sitter_languages` required
- Python 3.13 unsupported (upstream wheel availability)

## Repository Boundaries

- `src/sciona/runtime/`: paths, identity, logging, git, errors
- `src/sciona/data_storage/`: CoreDB/ArtifactDB schemas and access
- `src/sciona/code_analysis/`: discovery, parse, extraction, normalization, assembly
- `src/sciona/code_analysis/languages/builtin/`: builtin adapters (`python`, `typescript`, `javascript`, `java`)
- `src/sciona/code_analysis/languages/common/`: shared language extraction helpers
- `src/sciona/pipelines/`: build/reducer orchestration + policy checks
- `src/sciona/reducers/`: deterministic reducer payload generation
- `src/sciona/api/`: stable addon-facing API

Dependency direction is downward only across layers.

## Language Adapter Architecture

Pipeline:

```text
tree-sitter AST
  -> language adapter
  -> Structural IR (IRNode / IREdge / IRCall)
  -> IR Builder
  -> AnalysisResult
  -> Structural Assembler
  -> CoreDB snapshot
```

Adapter contract is `AdapterSpecV1` (descriptor-first registration).

Required descriptor fields:

- `language_id`
- `extensions`
- `grammar_name`
- `query_set_version`
- `callable_types`
- `module_namer`
- `extractor_factory`
- `capability_manifest_key`

JavaScript adapter modules are split by concern:

- `javascript_nodes.py`
- `javascript_imports.py`
- `javascript_calls.py`
- `javascript_resolution.py`

Non-negotiable ownership boundaries:

- `CALLS` strict materialization gate stays core-owned.
- Snapshot semantics and reducers stay core-owned.
- Adapters map syntax to structural IR only.

## Build Lifecycle

`pipelines.exec.build` high-level flow:

1. Validate repo/config policy.
2. Discover tracked files for enabled languages.
3. Parse and extract structural nodes/edges.
4. Compute structural hash and decide snapshot reuse/new commit.
5. Enforce one committed snapshot in CoreDB.
6. Rebuild ArtifactDB as a derivative of committed snapshot.

## Snapshot and Diff Overlay

- Committed snapshot is authoritative.
- Dirty-worktree `_diff` payloads are advisory only.
- For authoritative evidence, commit + `sciona build`.

## Addon API

Core runtime does not auto-discover/load addons.
Stable read-only addon surface is `sciona.api.addons`.

Exports:

- `PLUGIN_API_VERSION`, `PLUGIN_API_MAJOR`, `PLUGIN_API_MINOR`
- `list_entries(...)`
- `emit(...)`
- `open_core_readonly(...)`, `open_artifact_readonly(...)`
- `core_readonly(...)`, `artifact_readonly(...)`

Behavior:

- addon access is read-only;
- helpers resolve `repo_root` from CWD when omitted;
- `emit(...)` targets latest committed snapshot.

## Testing Workflow

Run tests in conda env `multiphysics`.

Baseline:

```bash
pytest -q
```

Required coverage themes for structural changes:

- contract/compliance invariants;
- determinism/stable ordering;
- cross-language parity (fixtures + score gate);
- strict `CALLS` gate behavior;
- tree-sitter policy constraints.
