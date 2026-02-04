# SCIONA Reducers

This document lists reducers available to prompt developers. Every reducer is
registered, deterministic (strict or conditional), and must expose exactly one
placeholder for prompt compilation.
This list is exhaustive but not normative; reducer availability does not imply
suitability for any specific prompt.

Snapshot policy:
- Reducers operate on the **latest committed snapshot only**.

---

## Reducer constraints

- Reducers read from SCI/Artifact DBs only; source files are used only to enrich
  known nodes (signatures, parameters, decorators, doc spans).
- Reducers never discover new nodes or infer relationships.
- No public reducer may be a pure alias of another reducer.

---

## Public reducer tiers (frozen)

Structural spine (core, required by tooling):
- structural_index
- module_overview
- callable_overview
- call_graph
- class_overview
- class_method_list
- class_inheritance

Baseline / control (public, non-core):
- callable_source
- concatenated_source

Derived / optional (public, non-core):
- fan_summary
- hotspot_summary
- class_call_graph
- module_call_graph
- callsite_index
- importers_index

Structural optional (public, non-core):
- symbol_lookup
- symbol_references
- file_outline
- module_file_map
- dependency_edges
- import_references

---

## Structural reducers (DB-derived, non-inferential)

| reducer_id | scope | placeholder | determinism | lossy | baseline_only | composite | summary |
| --- | --- | --- | --- | --- | --- | --- | --- |
| structural_index | codebase | STRUCTURAL_INDEX | strict | false | false | false | Canonical structural index payload for the codebase. |
| module_overview | module | MODULE_OVERVIEW | strict | false | false | false | Structural overview payload for a module. |
| class_overview | class | CLASS_OVERVIEW | strict | false | false | false | Structural overview payload for a class. |
| callable_overview | function | CALLABLE_OVERVIEW | strict | false | false | false | Structural overview payload for a callable (function or method). |
| class_inheritance | class | CLASS_INHERITANCE | strict | false | false | false | Class inheritance and interface relationships. |
| symbol_lookup | codebase | SYMBOL_LOOKUP | strict | false | false | false | Ranked symbol matches for a query. |
| symbol_references | codebase | SYMBOL_REFERENCES | strict | true | false | false | Relationship references (calls/imports) for symbols matching a query. |
| file_outline | codebase | FILE_OUTLINE | strict | false | false | false | File-level outline of modules, classes, and callables. |
| module_file_map | codebase | MODULE_FILE_MAP | strict | false | false | false | Module-to-file map with module ids and file paths. |
| dependency_edges | codebase | DEPENDENCY_EDGES | strict | true | false | false | Explicit module import edges for the snapshot. |
| import_references | codebase | IMPORT_REFERENCES | strict | true | false | false | Modules that import the target module(s). |

Notes:
- `callable_overview` accepts `function_id` or `method_id`.
- `callable_overview` also accepts `callable_id`.
- `module_overview` accepts `module_id` or resolves from `callable_id`, `function_id`, `method_id`, or `class_id`.
- `class_overview` accepts `class_id` or resolves from `method_id`.
- `class_inheritance` returns empty relationships unless inheritance edges are present in ArtifactDB.
- `symbol_lookup` accepts `query`, optional `kind` (including `any`), and optional `limit`.
- `symbol_references` accepts `query`, optional `kind` (including `any`), and optional `limit`.
- `file_outline` accepts optional `module_id` or `file_path` filters.
- `module_file_map` accepts optional `module_id` filtering.
- `dependency_edges` accepts optional `module_id`/`from_module_id`, `to_module_id`, `query` (source-module match when no ids provided), `edge_type`, and `limit`.
- `dependency_edges` includes `edge_source: sci` on each edge and at the top level.
- `import_references` accepts `module_id` or `query`, plus optional `edge_type` and `limit`.

---

## Summary reducers (lossy, prompt-oriented)

| reducer_id | scope | placeholder | determinism | lossy | baseline_only | composite | summary |
| --- | --- | --- | --- | --- | --- | --- | --- |
| call_graph | function | CALL_GRAPH | strict | true | false | false | Caller/callee call graph for a callable. |
| callsite_index | function | CALLSITE_INDEX | strict | true | false | false | Caller/callee edge index for a callable. |
| class_call_graph | class | CLASS_CALL_GRAPH | strict | true | false | false | Class-level call graph summary. |
| fan_summary | codebase | FAN_SUMMARY | strict | true | false | false | Fan-in/out summary for calls and imports. |
| hotspot_summary | codebase | HOTSPOT_SUMMARY | strict | true | false | false | Compressed codebase hotspot summary. |
| module_call_graph | module | MODULE_CALL_GRAPH | strict | true | false | false | Module-level call graph summary. |
| class_method_list | class | CLASS_METHOD_LIST | strict | true | false | false | List of methods for a class with basic visibility. |
| importers_index | codebase | IMPORTERS_INDEX | strict | true | false | false | Index of modules that import target module(s). |

Notes:
- `callsite_index` accepts `callable_id`, `function_id`, or `method_id` and returns CALLS edges from ArtifactDB when available.
  Each edge includes `edge_source`, optional `call_hash`, caller/callee language and node type metadata; `line_span`
  is null unless a callsite store is added in ArtifactDB.
- `callsite_index` accepts optional `direction`.
- `fan_summary` accepts optional `callable_id`, `function_id`, `method_id`, `class_id`, or `module_id` in addition to `scope=codebase`.
- `module_call_graph` accepts `module_id` or resolves from `callable_id`, `function_id`, `method_id`, or `class_id`.
- `class_call_graph` accepts `class_id` or resolves from `method_id`.
- `importers_index` accepts `module_id` or `query`, plus optional `edge_type` and `limit`.

---

## Composite reducers (curated orientations)

| reducer_id | scope | placeholder | determinism | lossy | baseline_only | composite | summary |
| --- | --- | --- | --- | --- | --- | --- | --- |

---

## Baseline reducers (control/baseline)

| reducer_id | scope | placeholder | determinism | lossy | baseline_only | composite | summary |
| --- | --- | --- | --- | --- | --- | --- | --- |
| callable_source | function | CALLABLE_SOURCE | conditional | true | true | false | Full source payload for a callable (function or method). |
| concatenated_source | codebase | CONCATENATED_SOURCE | conditional | true | true | false | Concatenated source for codebase, module, or class scope. |

Notes:
- `callable_source` accepts `callable_id`, `function_id`, or `method_id`.
- `concatenated_source` requires `scope` (`codebase`, `module`, or `class`); `module` requires `module_id`, `class` requires `class_id`.
