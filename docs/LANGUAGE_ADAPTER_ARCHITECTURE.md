# SCIONA Language Adapter Architecture

This document defines the extraction architecture for built-in and future
optional language adapters.

## Pipeline

```
tree-sitter AST
    -> language adapter (builtin or optional package)
    -> Structural IR (IRNode / IREdge / IRCall)
    -> IR Builder
    -> AnalysisResult
    -> Structural Assembler
    -> CoreDB snapshot
```

## Boundaries

- Core extraction contracts live in `src/sciona/code_analysis/core/extract/`.
- Language implementations live in:
  - `src/sciona/code_analysis/languages/builtin/`
  - `src/sciona/code_analysis/languages/common/`
- Legacy `core/extract/languages/` implementation modules are retired.

## Adapter Contract

`AdapterSpecV1` fields:

- `language_id`
- `extensions`
- `grammar_name`
- `query_set_version`
- `callable_types`
- `module_namer`
- `extractor_factory`
- `capability_manifest_key`

Descriptors are validated before analyzer routing.

## Invariants

- `CALLS` materialization gate remains core-owned.
- Snapshot semantics and reducers remain core-owned.
- Adapters perform syntax extraction and mapping only.
- IR stays minimal and structural (not a generic AST).
