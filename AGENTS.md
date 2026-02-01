<!-- sciona:begin -->
# SCIONA usage (managed)

Goal: maximize use of SCIONA CLI before manual inspection or ad-hoc scripts.

1) Invocation (confirm once per thread)
- Ask which command to use: `sciona …` or `conda run -n <env> sciona …` (only the first time in a thread).
- After the first answer, reuse that invocation without asking again.

2) Always start with ids
- Find candidates:
  `sciona search <query> --kind module|class|function|method|callable --limit 10`
- Resolve a specific id:
  `sciona resolve <identifier> --kind module|class|function|method|callable`

Note: if the worktree is dirty, outputs reflect the latest committed snapshot only.

3) Dirty worktree strategy (recommended)
- SCIONA reflects the last committed snapshot only.
- Use SCIONA for structure/calls/deps, then manually verify files you changed.
- For accurate SCIONA results on new/modified files, make small WIP commits and amend/squash later.

4) Common tasks (copy/paste templates)
Orientation:
- sciona reducer --id codebase_orientation
- sciona reducer --id structural_index

Structure (module/class/callable):
- sciona reducer --id module_summary [--module-id <module_id>] [--callable-id <callable_id>] [--function-id <function_id>] [--method-id <method_id>] [--class-id <class_id>]
- sciona reducer --id class_summary [--class-id <class_id>] [--method-id <method_id>]
- sciona reducer --id callable_summary [--callable-id <callable_id>] [--function-id <function_id>] [--method-id <method_id>]

Dependencies / imports:
- sciona reducer --id dependency_summary
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

Context bundle:
- sciona reducer --id callable_context_bundle [--callable-id <callable_id>] [--function-id <function_id>] [--method-id <method_id>] [--direction <direction>]

Code text (last resort):
- sciona reducer --id callable_source [--callable-id <callable_id>] [--function-id <function_id>] [--method-id <method_id>]
- sciona reducer --id concatenated_source [--scope <scope>] [--module-id <module_id>] [--class-id <class_id>] [--extras]

Public surface:
- sciona reducer --id public_surface_index [--module-id <module_id>] [--kind <kind>] [--limit <limit>]
Note: `public_surface_index` reports syntactic visibility, not API stability.

5) Reducer discovery
- `sciona reducer list`
- `sciona reducer info --id <reducer_id>`

6) Reporting (required)
- Prefer a compressed SCIONA evidence summary over raw dumps.
- After evidence, you may add a clearly labeled interpretation note.
- If worktree is dirty, say outputs reflect the latest committed snapshot only.

7) If SCIONA cannot answer
- State which command failed and why, then open files manually.

8) Troubleshooting
- "No committed snapshots" → run `sciona build`.
- "Unknown reducer" → run `sciona reducer list`.
<!-- sciona:end -->
