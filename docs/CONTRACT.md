# SCIONA Structural Contract

This contract defines the language-agnostic structural model SCIONA MUST emit.
It is authoritative for analysis and validation.

## Scope

- Applies to all supported languages.
- Applies to the single committed snapshot retained in CoreDB.
- Static, syntax-only analysis; no execution, no runtime inference.
- Extraction is tree-sitter query/field driven.
- Tree-sitter parser setup MUST be deterministic and use
  `tree_sitter.Parser` + `tree_sitter_languages.get_language`.
- A narrow parser bootstrap helper is allowed for multi-language growth.
- Allowed bootstrap scope is strictly:
  parser construction, language binding, and parser/grammar diagnostics.
- Bootstrap helper location is `src/sciona/code_analysis/core/extract/parser_bootstrap.py`.
- Query/extraction helpers MUST be separate from bootstrap helper code
  (for example `core/extract/query_helpers.py`).
- Bootstrap helper MUST NOT perform parsing fallback, extraction logic,
  language routing, or semantic behavior changes.
- General parser wrapper/factory abstractions remain out-of-contract.
- Structural extraction MUST fail closed for unsupported query node types.
- No heuristic traversal fallback is allowed for structural extraction.

## Structural Nodes

SCIONA MUST emit these structural node types:

- `module`
- `class`
- `function` (top-level only)
- `method` (class members only; constructors are represented as methods)

Synthetic nodes:

- Implementations MAY emit synthetic navigation nodes (for example `entry_point`).
- Synthetic nodes are out-of-contract for language compliance.
- Synthetic nodes MUST NOT be treated as language structural entities.

## Structural Edges

SCIONA MUST emit these edge types:

- `CONTAINS` (module -> class/function; class -> nested class)
- `DEFINES_METHOD` (class -> method)
- `IMPORTS_DECLARED` (module -> module)
- `CALLS` (callable -> callable, in-repo only)

Optional enrichment edges (MAY be emitted; not required for baseline compliance):

- `NESTS` (class -> nested class, disambiguates nested containment)
- `EXTENDS` (class-like -> class-like, local syntactic inheritance)
- `IMPLEMENTS` (class/record -> interface, local syntactic implementation)

## Edge Semantics

`CONTAINS`:

- `module` MUST contain only `class` and `function` nodes.
- `module` MUST NOT contain `method` nodes.
- `class` MAY contain nested `class` nodes.

`DEFINES_METHOD`:

- Constructors MUST be represented as `method` nodes.
- Constructor/member method ownership MUST be represented via `DEFINES_METHOD`.

`CALLS`:

- MUST represent syntactic call expressions only.
- MUST NOT represent attribute reads/writes or other non-call expressions.
- MUST be emitted only when the final accepted target is an in-repo callable.

## Naming and Identity

Module identity:

- Canonical module identity is path-derived via
  `module_name_from_path(repo_root, file_path)`.
- Canonical identity MUST be used for structural node identity and storage.

Qualified names:

- `class`: `{module}.{class_name}`
- `function`: `{module}.{function_name}`
- `method`: `{class}.{method_name}`

Alias usage:

- Language-specific module aliases MAY be used for resolution assistance.
- Aliases MUST NOT replace canonical module identity.

## Call Attribution and Materialization

Attribution:

- Calls are attributed to the nearest enclosing structural callable.
- Nested non-structural callables are implementation detail.
- Nested callable calls MUST be attributed to enclosing structural callable.
- Nested callables MUST NOT be emitted as structural nodes.

Materialization gate:

- Candidate resolution may produce provisional outcomes.
- Final CALLS emission MUST pass strict candidate selection.
- Non-accepted candidates (unresolved, ambiguous, external, disallowed provenance)
  MUST be dropped.

## Import Handling

- Import extraction is syntax-only.
- Import normalization maps syntax-level targets to module identities.
- External/unresolved imports are out-of-contract.

Optional metadata:

- Implementations MAY attach import metadata (for example `import_scope`).
- Metadata MUST NOT alter structural edge types or contract semantics.
- Implementations MAY attach structural enrichment metadata, including:
  - class/method kind hints,
  - local base/interface names,
  - module-level binding names,
  - ambiguous call candidate diagnostics.

## Determinism

Outputs MUST be deterministic, stably ordered, and snapshot-bound.

Stable ordering MUST be:

1. module path lexical order
2. qualified name lexical order
3. edges sorted by `(source, target, edge_type)`
