# SCIONA

SCIONA builds a **deterministic structural index (SCI)** for a *git* repository. It captures what exists in the code (modules, classes, functions, methods) and how entities are structurally connected. SCIONA is **snapshot-based, reducer-driven, and LLM-agnostic**. It does not execute code or perform semantic inference. Instead, SCIONA produces  explicit structural representations derived from tree-sitter parsing. Reducers serve as the **source of structural evidence**, rendering reproducible  facts from a committed snapshot. This deterministic representation can be used to stabilize tooling workflows, including LLM-assisted development.

## Why SCIONA exists

When working with large, long-lived codebases, we repeatedly observed the same pattern: LLM assistance initially improves productivity, but gradually becomes inconsistent.  Earlier assumptions drift. Structural constraints are forgotten. The model continues to generate plausible responses that no longer reflect the actual code. **This is not primarily an LLM failure. It is a context stability problem**.

In real software systems, correctness often depends on structural relationships. Most LLM tooling relies on embeddings, semantic retrieval, or dynamically assembled  context. While powerful, these approaches can be difficult to reproduce and hard to constrain across long sessions or refactors.

SCIONA takes a deliberately different path: it provides a stable structural snapshot that downstream tools can rely on. Rather than reconstructing structure heuristically, tools may reason over deterministic reducer outputs. **SCIONA is intentionally limited in scope. It provides structure - not interpretation.**

## Disclaimer

SCIONA was originally developed as an internal tool at MegaScienta to address limitations observed in LLM-assisted workflows. It has been tested in day-to-day development across several active projects and has shown promising results. However, broader real-world validation across diverse repositories is still ongoing. Feedback, issue reports, and field experience are highly appreciated. **Thank you and happy coding.**

## How SCIONA can be used

SCIONA can be used directly via its CLI or integrated into LLM-assisted workflows. During initialization, SCIONA optionally auto-generates an AGENTS.md file in the repository root. This file serves as a control surface for LLM copilots by explicitly specifying how SCIONA should be used during code reasoning. In this mode, the copilot is instructed to reason over reducer outputs rather than reconstructing structure heuristically from source text.

## Installation

Default install (from GitHub):

```bash
pip install git+https://github.com/megascienta/sciona
```

Install development dependencies and run tests:

```bash
git clone https://github.com/megascienta/sciona
cd sciona
pip install -e ".[dev]"
pytest -q
```

## Quick start

```bash
cd /path/to/repo
sciona init
$EDITOR .sciona/config.yaml   # enable languages
sciona build
sciona status
```

## Snapshot model

SCIONA indexes the **last committed snapshot**. Reducers are evaluated against that committed snapshot, not against uncommitted working tree state. If you change tracked source files, commit and run `sciona build` to refresh the snapshot before relying on reducer output.

If your worktree is dirty, some reducer outputs include an `_diff` payload describing a best‑effort overlay of uncommitted changes. `_diff` payload should be treated as advisory. Please use a clean commit and `sciona build` for authoritative results.

## Supported languages

Built-in analyzers currently include Python, TypeScript, and Java. Enable languages in `.sciona/config.yaml` after `sciona init`.

## Reducers usage

### Discovery

Explore available reducers:

```bash
sciona reducer list
sciona reducer --id module_overview --module-id pkg.mod
```

If node (module, classe, function, method) identifier is unknown:

```bash
sciona search QUERY [--kind KIND] [--limit LIMIT] [--json]
sciona resolve IDENTIFIER [--kind KIND] [--limit LIMIT] [--json]
```

### Available reducers:

- Canonical structural index payload for the codebase

```bash
sciona reducer --id structural_index
```

- Caller/callee call graph for a callable

```bash
sciona reducer --id call_graph [--callable-id <callable_id>] [--function-id <function_id>] [--method-id <method_id>]
```

- Caller/callee edge index for a callable

```bash
sciona reducer --id callsite_index [--callable-id <callable_id>] [--function-id <function_id>] [--method-id <method_id>] [--direction <direction>]
```

- Class-level call graph summary

```bash
sciona reducer --id class_call_graph [--class-id <class_id>] [--method-id <method_id>]
```

- Best-effort class inheritance derived from parsed base clauses

```bash
sciona reducer --id class_inheritance [--class-id <class_id>]
```

- Explicit module import edges for the snapshot

```bash
sciona reducer --id dependency_edges [--module-id <module_id>] [--from-module-id <from_module_id>] [--to-module-id <to_module_id>] [--query <query>] [--edge-type <edge_type>] [--limit <limit>]
```

- Fan-in/out summary for calls and imports

```bash
sciona reducer --id fan_summary [--callable-id <callable_id>] [--function-id <function_id>] [--method-id <method_id>] [--class-id <class_id>] [--module-id <module_id>]
```

- Modules that import the target module(s)

```bash
sciona reducer --id import_references [--module-id <module_id>] [--query <query>] [--edge-type <edge_type>] [--limit <limit>]
```

- Index of modules that import target module(s)

```bash
sciona reducer --id importers_index [--module-id <module_id>] [--query <query>] [--edge-type <edge_type>] [--limit <limit>]
```

- Module-level call graph summary

```bash
sciona reducer --id module_call_graph [--module-id <module_id>] [--callable-id <callable_id>] [--function-id <function_id>] [--method-id <method_id>] [--class-id <class_id>]
```

- Structural overview payload for a callable (function or method)

```bash
sciona reducer --id callable_overview [--callable-id <callable_id>] [--function-id <function_id>] [--method-id <method_id>]
```

- Full source payload for a callable (function or method)

```bash
sciona reducer --id callable_source [--callable-id <callable_id>] [--function-id <function_id>] [--method-id <method_id>]
```

- Structural overview payload for a class

```bash
sciona reducer --id class_overview [--class-id <class_id>] [--method-id <method_id>]
```

- File-level outline of modules, classes, and callables

```bash
sciona reducer --id file_outline [--module-id <module_id>] [--file-path <file_path>]
```

- Module-to-file map with module ids and file paths

```bash
sciona reducer --id module_file_map [--module-id <module_id>]
```

- Structural overview payload for a module

```bash
sciona reducer --id module_overview [--module-id <module_id>] [--callable-id <callable_id>] [--function-id <function_id>] [--method-id <method_id>] [--class-id <class_id>]
```

- Ranked symbol matches for a query

```bash
sciona reducer --id symbol_lookup [--query <query>] [--kind <kind>] [--limit <limit>]
```

- Relationship references (calls/imports) for symbols matching a query

```bash
sciona reducer --id symbol_references [--query <query>] [--kind <kind>] [--limit <limit>]
```

- Compressed codebase hotspot summary

```bash
sciona reducer --id hotspot_summary
```

- Concatenated source for codebase, module, or class scope

```bash
sciona reducer --id concatenated_source [--scope <scope>] [--module-id <module_id>] [--class-id <class_id>]
```
