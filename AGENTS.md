<!-- sciona:begin -->
# SCIONA agent protocol (authoritative)

This file defines how agents and copilots MUST use SCIONA when reasoning about this
repository. It is the authoritative control surface for SCIONA-based code reasoning.

Goal: enforce SCIONA-first discipline to anchor reasoning to structural truth,
reduce hallucinations, and keep analysis reproducible and scoped.

---

## Core invariants (stable)

These rules define the epistemic contract of SCIONA usage. They are stable across
tooling changes and MUST always be followed.

### Authority model
- SCIONA reducers produce authoritative structural evidence for the codebase.
- Reducer outputs reflect the **last committed snapshot**.

### SCIONA-first principle
- If SCIONA is installed and available, agents MUST use SCIONA CLI for any
  structural question **before** manual file inspection, ripgrep, or ad-hoc scripts.

### Evidence before interpretation
- Always present a compressed SCIONA evidence summary **before** conclusions
  or interpretations.
- Interpretation without prior evidence is invalid.

### Snapshot vs dirty worktree semantics
- SCIONA reflects the last committed snapshot only.
- If the worktree is dirty and reducer payloads include a `_diff` overlay:
  - treat `_diff` as **primary evidence** for uncommitted changes
  - `_diff` overlays are best-effort and must be labeled as such
- If the worktree is dirty and `_diff` is missing:
  - explicitly warn that SCIONA outputs may be stale
  - recommend committing and running `sciona build`

### Explicit failure declaration
- If SCIONA is unavailable or a command fails:
  - explicitly state that SCIONA could not be used
  - include the failing command and a brief error summary
  - only then proceed with manual inspection as a fallback

---

## Operational guidance (best-effort, tool-dependent)

The following rules encode current best practices for using SCIONA with LLM copilots.
They may evolve as tooling and copilot behavior change, but SHOULD be followed when applicable unless explicitly stated otherwise.

### Invocation handling
- Preferred invocation: `sciona …` (when available on PATH)
- If SCIONA is installed in a managed environment, invoke it via the appropriate
  environment wrapper (e.g. `conda run -n <env> sciona …`, `source <venv>/bin/activate && sciona …`, etc.)
Rules:
- Do NOT guess or invent environment managers.
- Reuse a known invocation within the same session/thread.
- If invocation context is unknown, ask ONCE how SCIONA should be invoked.
- If the user cannot answer, assume `sciona …` and attempt execution.
- If execution fails, follow the “explicit failure declaration” rule.

### Tracked file scope (derived from .sciona/config)

The following scope describes what SCIONA currently indexes.
It is informational and may change with configuration updates.

- Enabled languages: python
- Tracked file types: .py
- Discovery excludes: none

Notes:
- Files or languages outside this scope are invisible to SCIONA.
- Absence of structural evidence may be due to scope exclusion.
- If reasoning requires files or languages outside this tracked scope:
  - explicitly state that SCIONA cannot provide structural evidence for them
  - treat SCIONA evidence (if any) as incomplete for this question
  - proceed using default tools as a fallback, clearly labeling conclusions as non-SCIONA-based

### Always start with identifiers
- Discover candidates:
  `sciona search QUERY [--kind KIND] [--limit LIMIT] [--json]`
- Resolve a specific identifier:
  `sciona resolve IDENTIFIER [--kind KIND] [--limit LIMIT] [--json]`
If identifiers are unknown, `sciona search QUERY [--kind KIND] [--limit LIMIT] [--json]` satisfies the “start with ids” requirement.

### Reducer discovery and robustness
- If a reducer is unknown or a command fails:
  - run `sciona reducer list [--id REDUCER_ID]`
  - inspect details with `sciona reducer info [--id REDUCER_ID]`
- Prefer discovery over guessing reducer names or flags.

### Common reducer usage (templates)
Orientation:
- sciona reducer --id structural_index

Structure (module/class/callable):
- sciona reducer --id callable_overview [--callable-id <callable_id>] [--function-id <function_id>] [--method-id <method_id>]
- sciona reducer --id class_inheritance [--class-id <class_id>]
- sciona reducer --id class_overview [--class-id <class_id>] [--method-id <method_id>]
- sciona reducer --id module_overview [--module-id <module_id>] [--callable-id <callable_id>] [--function-id <function_id>] [--method-id <method_id>] [--class-id <class_id>]

Dependencies / imports:
- sciona reducer --id dependency_edges [--module-id <module_id>] [--from-module-id <from_module_id>] [--to-module-id <to_module_id>] [--query <query>] [--edge-type <edge_type>] [--limit <limit>]
- sciona reducer --id import_references [--module-id <module_id>] [--query <query>] [--edge-type <edge_type>] [--limit <limit>]
- sciona reducer --id importers_index [--module-id <module_id>] [--query <query>] [--edge-type <edge_type>] [--limit <limit>]

Calls / call graph:
- sciona reducer --id call_graph [--callable-id <callable_id>] [--function-id <function_id>] [--method-id <method_id>]
- sciona reducer --id callsite_index [--callable-id <callable_id>] [--function-id <function_id>] [--method-id <method_id>] [--direction <direction>]
- sciona reducer --id class_call_graph [--class-id <class_id>] [--method-id <method_id>]
- sciona reducer --id module_call_graph [--module-id <module_id>] [--callable-id <callable_id>] [--function-id <function_id>] [--method-id <method_id>] [--class-id <class_id>]

References / usages:
- sciona reducer --id symbol_lookup [--query <query>] [--kind <kind>] [--limit <limit>]
- sciona reducer --id symbol_references [--query <query>] [--kind <kind>] [--limit <limit>]

File navigation (codebase-scoped; filters supported):
- sciona reducer --id file_outline [--module-id <module_id>] [--file-path <file_path>]
- sciona reducer --id module_file_map [--module-id <module_id>]

Code text (last resort):
- sciona reducer --id callable_source [--callable-id <callable_id>] [--function-id <function_id>] [--method-id <method_id>]
- sciona reducer --id concatenated_source [--scope <scope>] [--module-id <module_id>] [--class-id <class_id>]

Summaries:
- sciona reducer --id fan_summary [--callable-id <callable_id>] [--function-id <function_id>] [--method-id <method_id>] [--class-id <class_id>] [--module-id <module_id>]
- sciona reducer --id hotspot_summary

### Reporting checklist (required for code reasoning)
Include this checklist explicitly in responses:

- SCIONA used: <command(s)>
- Dirty worktree: yes / no / unknown
- `_diff` used: yes / no / not available
- Snapshot warning stated: yes / no
- If SCIONA failed: command + error summarized: yes / no

Evidence summary format (compressed):
- Entities: <resolved module/class/callable ids>
- Key edges: <imports / calls / deps summary>
- Notes: <snapshot vs `_diff` separation, if applicable>

### Troubleshooting
- “No committed snapshots” → run `sciona build`
- “Unknown reducer” → run `sciona reducer list [--id REDUCER_ID]`
<!-- sciona:end -->
