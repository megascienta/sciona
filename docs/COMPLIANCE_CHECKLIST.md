# SCIONA Language Compliance Checklist

Use this checklist to verify each language implementation against the structural
contract in `docs/CONTRACT.md`.

## Global Compliance Requirements

- CoreDB retains exactly one authoritative committed snapshot.
- Emits core node types: `module`, `type`, `callable`.
- Callable role metadata is present and in `{declared,nested,bound,constructor}`.
- Optional synthetic nodes are allowed but excluded from language compliance.
- Emits edge types:
  `LEXICALLY_CONTAINS`, `IMPORTS_DECLARED`, `CALLS`, `EXTENDS`, `IMPLEMENTS`.
- `module` is lexical root; each non-`module` structural node has exactly one
  lexical parent.
- Parent span strictly encloses child span for `LEXICALLY_CONTAINS`.
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
- Unsupported query node types fail closed (partial parse metadata; no heuristic fallback).
- Final CALLS emission passes strict candidate gate; non-accepted candidates are dropped.
- `CALL_SITES` is observational only and does not alter structural truth.
- `CALL_SITES` rows exclude external callsites.

## Python Compliance

- `class_definition` maps to `type`.
- `function_definition` and `async_function_definition` map to `callable`.
- Nested named defs map to `callable` with role `nested`.
- Named lambda assignment bindings map to `callable` with role `bound`.
- `decorated_definition` contributes wrapped class/function node.
- `__init__.py` is treated as package module identity.
- Imports come from `import_statement` and `import_from_statement`.
- Calls are collected from `call` nodes and attributed by enclosing callable scope.

## TypeScript Compliance

- Class-like declarations map to `type`.
- Named function/method declarations map to `callable`.
- Nested named function declarations map to `callable` with role `nested`.
- Bound callable expressions (arrow/function expressions with stable bindings)
  map to `callable` with role `bound`.
- Object-literal methods bound to stable identifiers map to `callable` with role `bound`.
- Anonymous `export default` callables map to deterministic module callable bindings.
- Inline anonymous callbacks are non-structural.
- Imports are extracted from:
  - `import_statement`,
  - `export_statement`,
  - `lexical_declaration` require-assignment patterns.
- `import ... = require(...)` is represented under `import_statement` with `import_require_clause` in the current grammar build.
- Calls are collected from `call_expression`/`new_expression` and attributed by enclosing callable scope.

## Java Compliance

- Class-like types include class/interface/enum/record forms and map to `type`.
- Methods and constructors map to `callable`.
- Named local classes are structural `type` nodes.
- Lambda expressions are non-structural callables.
- Imports are extracted from `import_declaration`.
- Package-derived alias may assist resolution, but canonical module identity remains path-based.
- Calls are collected from:
  - `method_invocation`,
  - `object_creation_expression`,
  - `explicit_constructor_invocation`.

## Verification Guidance

For each language implementation, verify:

1. Node and edge type completeness against contract.
2. Lexical parent/containment invariants.
3. Capability manifest consistency against query surfaces (`docs/CAPABILITY_MANIFEST.json`).
4. Language parity quality thresholds remain green for PY/TS/Java.
5. Naming and canonical identity invariants.
6. Query-only extraction behavior (no fallback path).
7. Strict call-gate filtering behavior for CALLS materialization.
8. Deterministic ordering across repeated runs on unchanged committed snapshot.
