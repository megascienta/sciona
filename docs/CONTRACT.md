# SCIONA Structural Contract

This contract defines the language-agnostic structural model SCIONA MUST emit.
It is authoritative for analysis and validation.

## Scope

- Applies to all supported languages.
- Applies to the single committed snapshot retained in CoreDB.
- `node_instances` and `edges` facts are snapshot-bound by `snapshot_id`.
- `structural_nodes` identities are global and carry deterministic
  `created_snapshot_id` provenance.
- Static, syntax-only analysis; no execution, no runtime inference.
- Extraction is tree-sitter query/field driven.
- Tree-sitter parser setup MUST be deterministic and use
  `tree_sitter.Parser` + `tree_sitter_languages.get_language`.
- A narrow parser bootstrap helper is allowed for multi-language growth.
- Allowed bootstrap scope is strictly:
  parser construction, language binding, and parser/grammar diagnostics.
- Bootstrap helper location is
  `src/sciona/code_analysis/core/extract/parsing/parser_bootstrap.py`.
- Query/extraction helpers MUST be separate from bootstrap helper code
  (for example `core/extract/parsing/query_helpers.py`).
- Bootstrap helper MUST NOT perform parsing fallback, extraction logic,
  language routing, or semantic behavior changes.
- General parser wrapper/factory abstractions remain out-of-contract.
- Structural extraction MUST fail closed for unsupported query node types.
- No heuristic traversal fallback is allowed for structural extraction.

## Structural Nodes

SCIONA MUST emit these structural node types:

- `module`
- `classifier`
- `callable`

`classifier` is the language-agnostic structural node category for named,
nominal, class-family declarations. It covers entities such as classes and
other class-family declarations with stable structural identity. It does not
include modules or callables.

`callable` role metadata MUST classify each callable as one of:

- `declared`
- `nested`
- `bound`
- `constructor`

Promotion rule for `callable`:

- A callable is structural iff it introduces a callable body with a stable
  lexical binding in the current lexical parent.
- Inline anonymous callbacks without stable lexical binding MUST NOT be
  structural nodes.

Synthetic nodes:

- Implementations MAY emit synthetic navigation nodes (for example `entry_point`).
- Synthetic nodes are out-of-contract for language compliance.
- Synthetic nodes MUST NOT be treated as language structural entities.

## Structural Edges

SCIONA MUST emit these edge types:

- `LEXICALLY_CONTAINS` (lexical parent -> lexical child)
- `IMPORTS_DECLARED` (module -> module)
- `CALLS` (callable -> callable, in-repo only)
- `EXTENDS` (classifier -> classifier, local syntactic inheritance)
- `IMPLEMENTS` (classifier -> classifier, local syntactic implementation)

## Edge Semantics

`LEXICALLY_CONTAINS`:

- Structural hierarchy is a lexical tree per module.
- `module` is the only lexical root.
- Every non-`module` structural node MUST have exactly one lexical parent.
- Parent and child MUST be from the same module/file lexical tree.
- Parent source span MUST contain child source span.
- Parent and child source spans MUST NOT be identical.
- Graph MUST be acyclic.
- Allowed pairs:
  - `module -> classifier`
  - `module -> callable`
  - `classifier -> classifier`
  - `classifier -> callable`
  - `callable -> classifier`
  - `callable -> callable`

`CALLS`:

- MUST represent syntactic call expressions only.
- MUST NOT represent attribute reads/writes or other non-call expressions.
- MUST be emitted only when the final accepted target is an in-repo callable.

`EXTENDS`:

- MUST represent direct syntax-level base declarations only.
- MUST NOT require cross-file semantic inference.

`IMPLEMENTS`:

- MUST represent direct syntax-level interface implementation declarations only.
- MUST NOT be inferred from structural similarity or method matching.

## Naming and Identity

Module identity:

- Canonical module identity is path-derived via
  `module_name_from_path(repo_root, file_path)`.
- Canonical identity MUST be used for structural node identity and storage.

Qualified names:

- Qualified names MUST encode lexical ownership.
- Identifiers MAY include deterministic disambiguators when required.

Disambiguation:

- If multiple structural siblings share the same local name in one lexical parent,
  identity MUST be disambiguated deterministically by lexical order
  (`start_byte` ascending).

Alias usage:

- Language-specific aliases MAY be used for resolution assistance.
- Aliases MUST NOT replace canonical module identity.

## Call Attribution and Materialization

Attribution:

- Calls are attributed to the nearest enclosing structural callable node.
- Inline anonymous non-structural callable bodies attribute calls to their
  nearest enclosing structural callable node.

Materialization gate:

- Candidate resolution may produce provisional outcomes.
- Required resolution stages (receiver/instance mapping, alias narrowing, class
  scoped fallback, module scoped fallback) are executed in language-specific
  resolver paths before strict materialization.
- Final CALLS emission MUST pass strict candidate selection.
- Strict candidate selection is the final acceptance/materialization gate and
  MUST NOT be interpreted as the full resolution-stage pipeline.
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
  - callable role and modifiers,
  - local base/interface names,
  - module-level binding names,
  - ambiguous call candidate diagnostics.

## Artifacts Observability

`CALL_SITES` is an artifact-layer observational table.

- `CALLS` remains the only authoritative call edge truth for reducers.
- `CALL_SITES` MUST NOT define new structural entities or structural edges.
- `CALL_SITES` stores in-repo candidate-relevant callsite observations only.
- External callsites MUST NOT be persisted as rows in `CALL_SITES`.
- Derived reporting classifications on dropped callsites (for example
  `external_likely`) are observational metadata only and MUST NOT affect strict
  candidate acceptance or `CALLS` emission.

## Determinism

Outputs MUST be deterministic, stably ordered, and snapshot-bound.

Stable ordering MUST be:

1. module path lexical order
2. qualified name lexical order
3. edges sorted by `(source, target, edge_type)`

## Compliance Criteria

Language implementations MUST satisfy all criteria below.

Global criteria:

- CoreDB retains exactly one authoritative committed snapshot.
- Emits core node types: `module`, `classifier`, `callable`.
- Callable role metadata is present and in `{declared,nested,bound,constructor}`.
- Optional synthetic nodes are allowed but excluded from language compliance.
- Emits edge types:
  `LEXICALLY_CONTAINS`, `IMPORTS_DECLARED`, `CALLS`, `EXTENDS`, `IMPLEMENTS`.
- `module` is lexical root; each non-`module` structural node has exactly one
  lexical parent.
- Parent span contains child span and is not identical to child span for
  `LEXICALLY_CONTAINS`.
- Lexical structural graph is acyclic.
- Constructors are represented as `callable` with role `constructor`.
- Canonical module identity is path-derived (not alias-derived).
- Calls are attributed to nearest enclosing structural callable.
- Inline anonymous non-structural callables do not become structural nodes.
- CALLS targets are in-repo callable IDs only.
- Optional enrichment metadata may be present on nodes/modules
  (for example role/modifier/base/module-binding diagnostics).
- Extraction is tree-sitter query/field driven.
- Parser setup is deterministic and uses `tree_sitter.Parser` +
  `tree_sitter_languages.get_language`.
- A narrow parser bootstrap helper may be used only for:
  parser construction, language binding, and parser/grammar diagnostics.
- General parser wrappers/factories are not used.
- Structural extraction fallback traversal is not allowed.
- Unsupported query node types fail closed (partial parse metadata; no
  heuristic fallback).
- Final CALLS emission passes strict candidate gate; non-accepted candidates
  are dropped.
- `CALL_SITES` is observational only and does not alter structural truth.
- `CALL_SITES` rows exclude external callsites.

Python criteria:

- `class_definition` maps to `classifier`.
- `function_definition` and `async_function_definition` map to `callable`.
- Nested named defs map to `callable` with role `nested`.
- Named lambda assignment bindings map to `callable` with role `bound`.
- `decorated_definition` contributes wrapped class/function node.
- `__init__.py` is treated as package module identity.
- Imports come from `import_statement` and `import_from_statement`.
- Calls are collected from `call` nodes and attributed by enclosing callable
  scope.
- Python `classifier` currently means named class declarations.

TypeScript criteria:

- Class-like declarations map to `classifier`.
- Named function/method declarations map to `callable`.
- Nested named function declarations map to `callable` with role `nested`.
- Bound callable expressions (arrow/function expressions with stable bindings)
  map to `callable` with role `bound`.
- Object-literal methods bound to stable identifiers map to `callable` with
  role `bound`.
- Anonymous `export default` callables map to deterministic module callable
  bindings.
- Inline anonymous callbacks are non-structural.
- Imports are extracted from:
  - `import_statement`,
  - `export_statement`,
  - `lexical_declaration` require-assignment patterns,
  - `call_expression` dynamic `import()` with string literal targets.
- `import ... = require(...)` is represented under `import_statement` with
  `import_require_clause` in the current grammar build.
- Calls are collected from `call_expression`/`new_expression` and attributed by
  enclosing callable scope.
- Profiling/introspection class query surface includes
  `class_declaration`, `abstract_class_declaration`, `class_expression`.
- TypeScript `classifier` currently means class-family declarations captured by
  the extractor query surface above.

Java criteria:

- Class-family declarations include class/interface/enum/record forms and map to
  `classifier`.
- Methods and constructors map to `callable`.
- Methods on named local classes declared inside callable scopes map to
  `callable` role `nested` (constructors remain `constructor`).
- Named local classes are structural `classifier` nodes.
- Lambda expressions are non-structural callables.
- Imports are extracted from `import_declaration`.
- Package-derived alias may assist resolution, but canonical module identity
  remains path-based.
- Calls are collected from:
  - `method_invocation`,
  - `object_creation_expression`,
  - `explicit_constructor_invocation`.
- Profiling/introspection class query surface includes
  `class_declaration`, `interface_declaration`, `enum_declaration`,
  `record_declaration`.
- Java `classifier` currently means classes, interfaces, enums, and records.
