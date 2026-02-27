# SCIONA Language Compliance Checklist

Use this checklist to verify each language implementation against the structural
contract in `docs/CONTRACT.md`.

## Global Compliance Requirements

- CoreDB retains exactly one authoritative committed snapshot.
- Emits core node types: `module`, `class`, `function`, `method`.
- Optional synthetic nodes are allowed but excluded from language compliance.
- Emits edge types: `CONTAINS`, `DEFINES_METHOD`, `IMPORTS_DECLARED`, `CALLS`.
- Optional enrichment edges may be present:
  `NESTS`, `EXTENDS`, `IMPLEMENTS`, `CALLABLE_IMPORTS_DECLARED`.
- `module` MUST NOT contain `method` nodes.
- Nested classes are represented with class -> class `CONTAINS`.
- Constructors are represented as `method`.
- Canonical module identity is path-derived (not alias-derived).
- Qualified naming follows:
  - classes: `{module}.{class}` (nested classes extend scope),
  - functions: `{module}.{function}`,
  - methods: `{class}.{method}`.
- Calls are attributed to nearest enclosing structural callable.
- Nested non-structural callables are not emitted as structural nodes.
- CALLS targets are in-repo callable IDs only.
- Optional enrichment metadata may be present on nodes/modules
  (for example kind/decorator/base/module-binding diagnostics).
- Extraction is tree-sitter query/field driven.
- Parser setup is deterministic and uses `tree_sitter.Parser` +
  `tree_sitter_languages.get_language`.
- A narrow parser bootstrap helper may be used only for:
  parser construction, language binding, and parser/grammar diagnostics.
- General parser wrappers/factories are not used.
- Structural extraction fallback traversal is not allowed.
- Unsupported query node types fail closed (partial parse metadata; no heuristic fallback).
- Final CALLS emission passes strict candidate gate; non-accepted candidates are dropped.

## Python Compliance

- Top-level `function_definition` and `async_function_definition` map to `function`.
- Class-member `function_definition` and `async_function_definition` map to `method`.
- `decorated_definition` contributes wrapped class/function node; decorators do not add structural nodes.
- `__init__.py` is treated as package module identity.
- Imports come from `import_statement` and `import_from_statement`.
- Calls are collected from `call` nodes and attributed by enclosing callable scope.

## TypeScript Compliance

- `function_declaration` maps to `function`.
- `method_definition` inside class maps to `method`.
- Anonymous callables do not create `function` nodes.
- Anonymous callable class members may map to `method` when represented as class member callable forms.
- Imports are extracted from:
  - `import_statement`,
  - `export_statement`,
  - `lexical_declaration` require-assignment patterns.
- `import ... = require(...)` is represented under `import_statement` with `import_require_clause` in the current grammar build.
- Calls are collected from `call_expression` nodes and attributed by enclosing callable scope.

## Java Compliance

- Class-like types include class/interface/enum/record forms.
- Constructors are represented as `method`.
- Imports are extracted from `import_declaration`.
- Package-derived alias may assist resolution, but canonical module identity remains path-based.
- Calls are collected from:
  - `method_invocation`,
  - `object_creation_expression`,
  - `explicit_constructor_invocation`.

## Verification Guidance

For each language implementation, verify:

1. Node and edge type completeness against contract.
1. Capability manifest consistency against query surfaces (`docs/CAPABILITY_MANIFEST.json`).
1. Language parity quality thresholds remain green for PY/TS/Java.
2. Naming and canonical identity invariants.
3. Query-only extraction behavior (no fallback path).
4. Strict call-gate filtering behavior for CALLS materialization.
5. Deterministic ordering across repeated runs on unchanged committed snapshot.
