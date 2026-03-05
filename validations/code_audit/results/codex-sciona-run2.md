## Model

- GPT-5.2-Codex Copilot / VS Code
- SCIONA v0.9.0 + SCIONA-AGENTS.md

## Prompt

This is a clean thread. No prior knowledge is allowed.

You are performing a pre-release code audit.

Documentation is located in docs/.

Analyze the codebase and report:

– Critical misalignments with documented principles or contracts
– Structural design problems
– Potential security-relevant issues

Reference specific files and methods where applicable.

## Results

- worked for 1m 35s
- explored 6 files, 4 searches, 1 lists

**Critical Misalignments**
- Contract violation: lexical orphans detected (non-`module` nodes lacking a lexical parent), which conflicts with `docs/CONTRACT.md` requirement that every non-`module` structural node must have exactly one lexical parent and the lexical graph is acyclic. Evidence: telemetry.
- Affected structural nodes (25 total) include:
- `src/sciona/cli/commands/register_agents.py` → `register_agents.agents`
- `src/sciona/cli/commands/register_build.py` → `register_build.build`
- `src/sciona/cli/commands/register_hooks.py` → `register_hooks.install`
- `src/sciona/cli/commands/register_hooks.py` → `register_hooks.remove`
- `src/sciona/cli/commands/register_hooks.py` → `register_hooks.status`
- `src/sciona/cli/commands/register_init.py` → `register_init.init`
- `src/sciona/cli/commands/register_status.py` → `register_status.clean`
- `src/sciona/cli/commands/register_status.py` → `register_status.status`
- `src/sciona/cli/main.py` → `_patch_click_make_metavar._make_metavar`
- `src/sciona/cli/main.py` → `_patch_typer_argument_make_metavar._make_metavar`
- `src/sciona/cli/reducer.py` → `register._emit_reducer_info`
- `src/sciona/cli/reducer.py` → `register.info_reducers`
- `src/sciona/cli/reducer.py` → `register.list_reducers`
- `src/sciona/cli/reducer.py` → `register.reducer`
- `src/sciona/cli/render.py` → `render_status._format_ts`
- `src/sciona/cli/resolve.py` → `register.resolve`
- `src/sciona/cli/search.py` → `register.search`
- `src/sciona/cli/utils.py` → `agents_command_map._pick`
- `src/sciona/code_analysis/languages/builtin/python/python_imports.py` → `collect_python_import_model._append_module`
- `src/sciona/code_analysis/languages/builtin/python/python_resolution_instances.py` → `collect_callable_instance_map.walk`
- `src/sciona/code_analysis/languages/builtin/python/python_resolution_instances.py` → `collect_callable_local_bindings.walk`
- `src/sciona/code_analysis/languages/builtin/python/python_resolution_instances.py` → `collect_class_instance_map.walk`
- `src/sciona/code_analysis/languages/builtin/python/python_resolution_instances.py` → `collect_module_instance_map.walk`
- `src/sciona/code_analysis/languages/builtin/typescript/typescript_node_walk.py` → `walk_typescript_nodes._emit_bound_callable`
- `src/sciona/pipelines/diff_overlay/affection.py` → `scoped_affection._call_match`

**Structural Design Problems**
- High import fan-out concentrated in diff overlay pipeline modules suggests tight coupling and brittle change surface in `src/sciona/pipelines/diff_overlay/*` (notably `compute_core`, `compute_config`, `compute_payloads`, `compute_summary`, `ops_get`). Evidence: telemetry.
- High import fan-in to `src/sciona/runtime`, `src/sciona/reducers/helpers/render`, `src/sciona/reducers/helpers/utils`, and `src/sciona/code_analysis/core/normalize/model` indicates centralization and potential layering pressure points. Evidence: telemetry.

**Potential Security-Relevant Issues**
- No high-confidence critical security findings surfaced in this pass.
- Caution: reducer registry uses reflective imports of modules under `src/sciona/reducers/*` at import time. If an attacker can write to the installed package or the repo used for execution, this enables arbitrary code execution on import. This is typical for plugin-style registries but worth acknowledging in threat modeling. Evidence: source.

**Status (Strict Mode)**
- sciona used: yes
- worktree: dirty
- diff: unavailable (`overlay_available` false)
- warned: yes

**Evidence**
- telemetry: `structural_integrity_summary` (lexical orphans), `hotspot_summary` (fan-in/out)
- overlay_advisory: `overlay_impact_summary` (overlay unavailable)

If you want, I can drill into any of the orphaned nodes to trace how they were emitted and propose targeted fixes.

**Next steps (optional)**
1. I can trace one or two orphaned nodes with `callable_overview` and `file_outline` to identify the extraction bug and suggest fixes.
2. I can review the diff overlay pipeline structure in more detail to validate whether the coupling is intentional or a layering violation.