# SCIONA Language Compliance Checklist

Use this checklist to verify each language implementation against the structural contract.

## Common Requirements (All Languages)

- Emits node types: `module`, `class`, `function`, `method`.
- Optional synthetic nodes (for example `entry_point`) are allowed for
  navigation and are excluded from language compliance checks.
- Emits edge types: `CONTAINS`, `DEFINES_METHOD`, `IMPORTS_DECLARED`, `CALLS`.
- `module` MUST NOT contain `method` nodes (use `DEFINES_METHOD` from class).
- Constructors are represented as `method` nodes.
- Uses canonical module identity from repo-relative path.
- Qualified names follow `{module}.{class}` and `{module}.{function}` and `{class}.{method}`.
- Calls are attributed to nearest enclosing structural callable.
- Nested callables are not emitted as structural nodes.
- CALLS targets are qualified names when resolvable, else terminal identifiers only.
- Imports are syntax-only and normalized to module names.
- Outputs are deterministic and stably ordered.

## Python

- `__init__.py` is treated as package module identity.
- `function_definition` at top level maps to `function`.
- `function_definition` inside class maps to `method`.
- `import_statement` and `import_from_statement` emit `IMPORTS_DECLARED`.
- Calls collected from `call` nodes and attributed to enclosing callable.

## TypeScript

- Declarations and expressions produce structural callables (coverage parity).
- Anonymous callables MUST NOT create `function` nodes.
- Anonymous callables MAY create `method` nodes only when assigned to class members.
- `method_definition` inside class maps to `method`.
- `function_declaration` maps to `function`.
- Import extraction includes `import_statement`, re-exports, and `import=`/`require` forms if present.
- Calls collected from `call_expression` nodes and attributed to enclosing callable.

## Java

- Class types include `class`, `interface`, `enum`, `record`.
- Constructors are treated as `method`.
- Imports extracted from `import_declaration`.
- Module alias uses package name for import resolution, canonical identity remains path-based.
- Calls collected from method invocations and constructor invocations.
