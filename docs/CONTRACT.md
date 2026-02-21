# SCIONA Structural Contract

This contract defines the minimal, language-agnostic structural model that all
supported languages MUST produce. It is authoritative for analysis and
validation.

## Scope

- Applies to all supported languages.
- Applies to committed snapshots only.
- Static, syntax-only analysis; no semantic inference or execution.

## Node Types

SCIONA MUST emit these structural node types for all languages:

- `module`
- `class`
- `function` (top-level only)
- `method` (class members only)

Non-core synthetic nodes:

- Implementations MAY emit synthetic navigation nodes (for example:
  `entry_point`) for repository-level entry anchoring.
- Synthetic nodes are out-of-contract for language compliance and MUST NOT be
  interpreted as language structural entities.
- A snapshot MAY contain multiple synthetic entry anchors.

## Edge Types

SCIONA MUST emit these edge types for all languages:

- `CONTAINS` (module → class/function)
- `DEFINES_METHOD` (class → method)
- `IMPORTS_DECLARED` (module → module)
- `CALLS` (callable → identifier, best-effort)

## Edge Semantics

CONTAINS:

- `module` MUST contain `class` and `function` nodes only.
- `module` MUST NOT contain `method` nodes.

DEFINES_METHOD:

- Constructors MUST be represented as `method` nodes.
- Constructors MUST be linked via `DEFINES_METHOD`.

CALLS:

- CALLS edges MUST represent syntactic call expressions only.
- CALLS MUST NOT represent attribute reads/writes or non-call expressions.
- Targets MUST follow the rule in "CALLS Target Semantics".

## Naming Rules

Module identity:

- Canonical module identity is derived from repo-relative path:
  `module_name_from_path(repo_root, file_path)`.
- This identity MUST be used for node identity and storage.

Qualified names:

- `class`: `{module}.{class_name}`
- `function`: `{module}.{function_name}`
- `method`: `{class}.{method_name}`

Optional alias:

- A language MAY store a module alias for import resolution only.
- Alias MUST NOT replace canonical module identity.

## CALLS Target Semantics

- If a call target is structurally resolvable, the target MUST be emitted as a
  qualified name.
- If not structurally resolvable, the target MUST be emitted as a terminal
  identifier string only.
- Mixed representations (some qualified, some terminal for the same target
  class) MUST NOT occur within the same snapshot.

## Call Attribution

- Calls are attributed to the nearest enclosing structural callable.
- Nested callables are treated as implementation detail; their calls are
  attributed to the enclosing structural callable.

Optional:

- Nested callables MAY be emitted as nodes, but their CALLS edges MUST still be
  attributed to the enclosing structural callable.
- Calls are identifier-only; no semantic resolution.

## Import Handling

- Syntax-only extraction.
- Normalization maps import targets to module names (canonical or alias).
- External or unresolved imports are out-of-contract.

Optional metadata:

- Implementations MAY tag imports with `import_scope` metadata
  (`internal`, `external`, `unknown`) without changing edge types.

## Determinism

- Outputs MUST be deterministic, stably ordered, and snapshot-bound.
- Ordering MUST be stable by:
  1. module path lexical order
  2. qualified name lexical order
  3. edges sorted by (source, edge_type, target)
