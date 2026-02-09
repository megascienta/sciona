<!-- sciona:begin -->
# SCIONA usage (managed)

Goal: always use SCIONA CLI first when installed, before manual inspection or ad-hoc scripts.

Intent: SCIONA-first discipline anchors LLM reasoning to structural truth, reduces
hallucinations, and keeps answers deterministic and scoped.

Tracked File Scope (from .sciona/config)
- Enabled languages: python
- Tracked file types: .py
- Discovery excludes: none

Mandatory rules (non-optional):
- Use SCIONA first for any structural question if installed and available.
- Do not open files or use ripgrep before SCIONA unless SCIONA fails.
- Ask once per thread for invocation; never ask again; always reuse the chosen invocation.
- If worktree is dirty and `_diff` exists, treat `_diff` as primary evidence.
- Always include a compressed SCIONA evidence summary before conclusions.
- If SCIONA output is stale or `_diff` is missing for a dirty worktree, remind the user to commit and run `sciona build`.

Minimum required behavior:
1. Use SCIONA before touching files.
2. State snapshot vs dirty status.
3. Provide a short evidence summary.
4. Only interpret after evidence.

Compliance checklist (must include in responses when reasoning about code):
- SCIONA used: <command>
- Dirty worktree: yes/no
- _diff used: yes/no (if no, state why)
- Snapshot warning stated: yes/no

1) Invocation (confirm once per thread)
- Ask which command to use: `sciona …` or `conda run -n <env> sciona …` (only the first time in a thread).
- After the first answer, reuse that invocation without asking again.
If invocation context is lost, re-ask once and explicitly state context was unavailable.

2) Always start with ids
- Find candidates:
  `sciona search <query> --kind module|class|function|method|callable --limit 10`
- Resolve a specific id:
  `sciona resolve <identifier> --kind module|class|function|method|callable`
When identifiers are unknown, `sciona search` satisfies the "start with ids" rule.

Note: if the worktree is dirty, outputs reflect the latest committed snapshot only.
If a reducer payload includes `_diff`, use the overlay as the primary evidence
for dirty-worktree changes and clearly separate it from committed snapshot data.

3) Dirty worktree strategy (recommended)
- SCIONA reflects the last committed snapshot only.
- When `_diff` is present, use it as the primary evidence for dirty-worktree changes.
- Use SCIONA for structure/calls/deps, then manually verify files you changed when needed.
- For accurate SCIONA results on new/modified files, make small WIP commits and amend/squash later.
- Dirty worktrees may include `_diff` overlays in reducer payloads; overlays are best-effort only.
- Reducer outputs are authoritative evidence; explanatory payloads are non-authoritative.
- `_diff` overlays include nodes/edges and may include call-edge diffs and summary stats.
- `sciona build` clears any diff overlay tables on clean head before rebuilding artifacts.

4) Common tasks (copy/paste templates)
Orientation:
- sciona reducer --id structural_index

Structure (module/class/callable):
- sciona reducer --id module_overview [--module-id <module_id>] [--callable-id <callable_id>] [--function-id <function_id>] [--method-id <method_id>] [--class-id <class_id>]
- sciona reducer --id class_overview [--class-id <class_id>] [--method-id <method_id>]
- sciona reducer --id callable_overview [--callable-id <callable_id>] [--function-id <function_id>] [--method-id <method_id>]

Dependencies / imports:
- sciona reducer --id dependency_edges [--module-id <module_id>] [--from-module-id <from_module_id>] [--to-module-id <to_module_id>] [--query <query>] [--edge-type <edge_type>] [--limit <limit>]
- sciona reducer --id importers_index [--module-id <module_id>] [--query <query>] [--edge-type <edge_type>] [--limit <limit>]

Calls / call graph:
- sciona reducer --id call_graph [--callable-id <callable_id>] [--function-id <function_id>] [--method-id <method_id>]
- sciona reducer --id callsite_index [--callable-id <callable_id>] [--function-id <function_id>] [--method-id <method_id>] [--direction <direction>]

References / usages:
- sciona reducer --id symbol_references [--query <query>] [--kind <kind>] [--limit <limit>]

File navigation (codebase-scoped; filters supported):
- sciona reducer --id module_file_map [--module-id <module_id>]
- sciona reducer --id file_outline [--module-id <module_id>] [--file-path <file_path>]

Code text (last resort):
- sciona reducer --id callable_source [--callable-id <callable_id>] [--function-id <function_id>] [--method-id <method_id>]
- sciona reducer --id concatenated_source [--scope <scope>] [--module-id <module_id>] [--class-id <class_id>]

5) Reducer discovery
- `sciona reducer list`
- `sciona reducer info --id <reducer_id>`

6) Reporting (required)
- Prefer a compressed SCIONA evidence summary over raw dumps.
- After evidence, you may add a clearly labeled interpretation note.
- If worktree is dirty, say outputs reflect the latest committed snapshot only.
- If `_diff` is present, call it out explicitly as overlay data and use it as the primary evidence for dirty changes.
Reports missing the compliance checklist are considered incomplete.

7) If SCIONA cannot answer
- State which command failed and why, then open files manually.

8) Troubleshooting
- "No committed snapshots" → run `sciona build`.
- "Unknown reducer" → run `sciona reducer list`.
<!-- sciona:end -->
