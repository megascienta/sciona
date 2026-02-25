# SCIONA Language Compliance Checklist

Use this checklist to verify each language implementation against the structural contract.

## Common Requirements (All Languages)

- CoreDB retains exactly one committed snapshot (singleton authoritative state).
- Emits node types: `module`, `class`, `function`, `method`.
- Optional synthetic nodes (for example `entry_point`) are allowed for
  navigation and are excluded from language compliance checks.
- Emits edge types: `CONTAINS`, `DEFINES_METHOD`, `IMPORTS_DECLARED`, `CALLS`.
- `module` MUST NOT contain `method` nodes (use `DEFINES_METHOD` from class).
- Nested classes are allowed via `CONTAINS` from `class` → `class`.
- Constructors are represented as `method` nodes.
- Uses canonical module identity from repo-relative path.
- Qualified names follow structural nesting:
  - classes: `{module}.{class}` with nested classes extending scope (for example `{module}.{outer}.{inner}`),
  - functions: `{module}.{function}`,
  - methods: `{class}.{method}`.
- Calls are attributed to nearest enclosing structural callable.
- Nested callables are not emitted as structural nodes.
- CALLS targets are in-repo callable ids only; unresolved/external targets are excluded.
- Imports are syntax-only and normalized to module names.
- Outputs are deterministic and stably ordered.

## Python

- Nested classes are represented with nested qualified names and class → class `CONTAINS`.
- `__init__.py` is treated as package module identity.
- `function_definition` and `async_function_definition` at top level map to `function`.
- `function_definition` and `async_function_definition` inside class map to `method`.
- `decorated_definition` contributes its wrapped class/function node; decorators do not add structural nodes.
- `import_statement` and `import_from_statement` emit `IMPORTS_DECLARED`.
- Calls collected from `call` nodes and attributed to enclosing callable.

## TypeScript

- Nested classes are represented with nested qualified names and class → class `CONTAINS`.
- Declarations and expressions produce structural callables (coverage parity).
- Anonymous callables MUST NOT create `function` nodes.
- Anonymous callables MAY create `method` nodes only when assigned to class members.
- Nested classes are represented with nested qualified names.
- `method_definition` inside class maps to `method`.
- `function_declaration` maps to `function`.
- Import extraction includes `import_statement`, re-exports, and `import=`/`require` forms if present.
- Calls collected from `call_expression` nodes and attributed to enclosing callable.

## Java

- Nested class types are represented with nested qualified names and class → class `CONTAINS`.
- Class types include `class`, `interface`, `enum`, `record`.
- Nested class types are represented with nested qualified names.
- Constructors are treated as `method`.
- Imports extracted from `import_declaration`.
- Module alias uses package name for import resolution, canonical identity remains path-based.
- Calls collected from method invocations and constructor invocations.
