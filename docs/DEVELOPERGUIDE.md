# SCIONA Developer Guide

This guide defines current implementation boundaries, invariants, and workflow
rules for contributors.

Authoritative references:

- Contract: `docs/CONTRACT.md`
- Compliance: `docs/COMPLIANCE_CHECKLIST.md`
- Capability parity matrix: `docs/CAPABILITY_MATRIX.md`
- Generated capability manifest: `docs/CAPABILITY_MANIFEST.json`

If this guide conflicts with those files, contract/compliance wins.

## System Purpose

SCIONA builds a deterministic Structural Code Index (SCI) for a committed
repository snapshot. It models static structure and relations only.

Out of scope:

- Runtime behavior
- Dynamic dispatch certainty
- Dependency-injection wiring certainty
- Reflection/monkey-patching/runtime mutation

## Core Invariants

- Deterministic output for the same committed repo state, config, and version.
- Committed snapshot is authoritative.
- CoreDB holds one authoritative committed snapshot.
- ArtifactDB is derived from committed SCI and does not mutate SCI facts.
- Reducers are deterministic and read-only.
- Structural extraction is tree-sitter query/field driven.
- No heuristic fallback traversal for structural extraction.
- Unsupported query node types fail closed (partial parse metadata), not fallback.
- Code-analysis profiling helpers are tree-sitter driven; non-tree-sitter parser fallbacks are disallowed.
- Code-analysis parser setup uses direct `tree_sitter.Parser` +
  `tree_sitter_languages.get_language`; parser wrapper/factory modules are disallowed.

## Runtime Requirements

- Python: 3.11 or 3.12
- `tree_sitter_languages` required
- Python 3.13 currently unsupported (upstream wheel availability)

## Package Boundaries

- `src/sciona/runtime/`: runtime utilities (paths, identity, logging, git, errors)
- `src/sciona/data_storage/`: CoreDB/ArtifactDB schemas and storage operations
- `src/sciona/code_analysis/`: discovery, parse, extraction, normalization, assembly
- `src/sciona/pipelines/`: build/reducer orchestration and policy enforcement
- `src/sciona/reducers/`: deterministic reducer payload generation
- `src/sciona/api/`: stable addon-facing API

Dependency direction:

- No upward imports across layers.
- Exception: pipelines may import reducer registry/context/payload wiring.

## Build Lifecycle

`pipelines.exec.build` high-level flow:

1. Validate repository and config policy.
2. Discover tracked files for enabled languages.
3. Parse and extract structural nodes/edges.
4. Compute structural hash and decide snapshot reuse/new commit.
5. Enforce single committed snapshot in CoreDB.
6. Rebuild ArtifactDB as a pure derivative of committed snapshot.

## Snapshot and Diff Overlay Policy

- Authoritative evidence is committed snapshot data.
- Dirty worktree overlays (`_diff`) are best-effort reducer hints only.
- `_diff` does not replace SCI evidence.
- Dirty checks apply to tracked files/languages in `.sciona/config.yaml` scope.

## Extraction and Resolution Model

Parsing and extraction:

- Tree-sitter parser per language.
- Query API for node capture and field-driven extraction.
- No DFS fallback traversal for structural extraction.

Calls:

- Call sites are syntax-derived and best-effort.
- Attribution is based on nearest enclosing structural callable.
- Resolution uses deterministic shared kernel path.
- Final materialization is contract-gated via strict call candidate selection.
- Only accepted in-repo callable targets become `CALLS` edges.

Imports:

- Syntax-only extraction and normalization.
- External/unresolved imports are not emitted as internal structural edges.

## Supported Languages

- Python
- TypeScript
- Java

## Current Language Extraction Surface

Python:

- Imports: `import_statement`, `import_from_statement`
- Calls: `call`

TypeScript:

- Imports: `import_statement`, `export_statement`, `lexical_declaration` require-assignment patterns
- Calls: `call_expression`
- Note: `import ... = require(...)` is covered through `import_statement` / `import_require_clause` in the current grammar; there is no standalone `import_equals_declaration` node in this build.

Java:

- Imports: `import_declaration`
- Java import normalization includes class aliases, static member aliases, and static wildcard owner targets.
- Calls: `method_invocation`, `object_creation_expression`, `explicit_constructor_invocation`

## Data Model

CoreDB (authoritative):

- `snapshots`
- `structural_nodes`
- `node_instances`
- `edges`

ArtifactDB (derived):

- `node_status`
- `node_calls`
- `graph_nodes`
- `graph_edges`
- Rollups: `module_call_edges`, `class_call_edges`, `node_fan_stats`
- Optional overlay tables: `diff_overlay*`

## Reducer Rules

- Reducers are deterministic, read-only, and snapshot-bound.
- Reducers may enrich representation of known nodes.
- Reducers must not discover/define new structural entities.
- Reducer pipeline validates diff mode and identifier resolution against committed SCI.

## Addon Rules

Core runtime does not dynamically discover/load addons.

- Stable addon API: `sciona.api.addons`
- Addons may consume reducers and read storage through exposed APIs.
- Addons must not mutate snapshot/artifact state directly.

## Testing Expectations

Mandatory coverage themes:

- Contract/compliance invariants
- Determinism and stable ordering
- Cross-language parity on shared fixtures (hand-authored + generated)
- Parity score hard-gate (`tests/code_analysis/test_language_parity_score_gate.py`)
- Build/reducer boundary correctness
- Strict call-gate behavior for `CALLS` emission
- Policy gates for tree-sitter-only extraction/profiling behavior

Run baseline test suite:

```bash
pytest -q
```

Repository policy for this workspace requires running tests in conda env
`multiphysics`.
