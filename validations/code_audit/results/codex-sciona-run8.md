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

- worked for 2m 13s
- explored 3 files, 2 searches, 0 lists

**Findings (High Priority)**
1. **Contract violation: lexical orphans in committed snapshot (critical).**  
The structural contract requires every non-`module` node to have exactly one lexical parent via `LEXICALLY_CONTAINS`. The committed SCI snapshot reports `integrity_ok=false` with **25 lexical orphans**, which violates the contract and undermines reducer correctness.  
structural evidence: `structural_integrity_summary`  
overlay_advisory: `_diff` unavailable (see Status)

Affected callables (structural orphans):
1. `src/sciona/cli/commands/register_agents.py` — `sciona.src.sciona.cli.commands.register_agents.register_agents.agents`
2. `src/sciona/cli/commands/register_build.py` — `sciona.src.sciona.cli.commands.register_build.register_build.build`
3. `src/sciona/cli/commands/register_hooks.py` — `sciona.src.sciona.cli.commands.register_hooks.register_hooks.install`
4. `src/sciona/cli/commands/register_hooks.py` — `sciona.src.sciona.cli.commands.register_hooks.register_hooks.remove`
5. `src/sciona/cli/commands/register_hooks.py` — `sciona.src.sciona.cli.commands.register_hooks.register_hooks.status`
6. `src/sciona/cli/commands/register_init.py` — `sciona.src.sciona.cli.commands.register_init.register_init.init`
7. `src/sciona/cli/commands/register_status.py` — `sciona.src.sciona.cli.commands.register_status.register_status.clean`
8. `src/sciona/cli/commands/register_status.py` — `sciona.src.sciona.cli.commands.register_status.register_status.status`
9. `src/sciona/cli/main.py` — `sciona.src.sciona.cli.main._patch_click_make_metavar._make_metavar`
10. `src/sciona/cli/main.py` — `sciona.src.sciona.cli.main._patch_typer_argument_make_metavar._make_metavar`
11. `src/sciona/cli/reducer.py` — `sciona.src.sciona.cli.reducer.register._emit_reducer_info`
12. `src/sciona/cli/reducer.py` — `sciona.src.sciona.cli.reducer.register.info_reducers`
13. `src/sciona/cli/reducer.py` — `sciona.src.sciona.cli.reducer.register.list_reducers`
14. `src/sciona/cli/reducer.py` — `sciona.src.sciona.cli.reducer.register.reducer`
15. `src/sciona/cli/render.py` — `sciona.src.sciona.cli.render.render_status._format_ts`
16. `src/sciona/cli/resolve.py` — `sciona.src.sciona.cli.resolve.register.resolve`
17. `src/sciona/cli/search.py` — `sciona.src.sciona.cli.search.register.search`
18. `src/sciona/cli/utils.py` — `sciona.src.sciona.cli.utils.agents_command_map._pick`
19. `src/sciona/code_analysis/languages/builtin/python/python_imports.py` — `sciona.src.sciona.code_analysis.languages.builtin.python.python_imports.collect_python_import_model._append_module`
20. `src/sciona/code_analysis/languages/builtin/python/python_resolution_instances.py` — `sciona.src.sciona.code_analysis.languages.builtin.python.python_resolution_instances.collect_callable_instance_map.walk`
21. `src/sciona/code_analysis/languages/builtin/python/python_resolution_instances.py` — `sciona.src.sciona.code_analysis.languages.builtin.python.python_resolution_instances.collect_callable_local_bindings.walk`
22. `src/sciona/code_analysis/languages/builtin/python/python_resolution_instances.py` — `sciona.src.sciona.code_analysis.languages.builtin.python.python_resolution_instances.collect_class_instance_map.walk`
23. `src/sciona/code_analysis/languages/builtin/python/python_resolution_instances.py` — `sciona.src.sciona.code_analysis.languages.builtin.python.python_resolution_instances.collect_module_instance_map.walk`
24. `src/sciona/code_analysis/languages/builtin/typescript/typescript_node_walk.py` — `sciona.src.sciona.code_analysis.languages.builtin.typescript.typescript_node_walk.walk_typescript_nodes._emit_bound_callable`
25. `src/sciona/pipelines/diff_overlay/affection.py` — `sciona.src.sciona.pipelines.diff_overlay.affection.scoped_affection._call_match`

These orphans must be resolved before release; they violate the structural contract and may break reducers that assume a valid lexical tree.

---

**Structural Design Issues (Moderate)**
1. **Diff overlay subsystem is a high-coupling hotspot.**  
Telemetry shows very high import fan‑out for:
- `sciona.src.sciona.pipelines.diff_overlay.compute_core`
- `sciona.src.sciona.pipelines.diff_overlay.compute_config`
- `sciona.src.sciona.pipelines.diff_overlay.compute_payloads`
- `sciona.src.sciona.pipelines.diff_overlay.compute_summary`
- `sciona.src.sciona.pipelines.diff_overlay.ops_get`

This indicates the diff overlay pipeline is structurally central and likely has a large blast radius when changed. Consider reducing fan‑out or splitting responsibilities to improve stability.  
telemetry evidence: `hotspot_summary`

2. **Rendering and normalization modules are high fan‑in hotspots.**  
Telemetry shows high import fan‑in for:
- `sciona.src.sciona.reducers.helpers.render`
- `sciona.src.sciona.code_analysis.core.normalize.model`
- `sciona.src.sciona.runtime`
- `sciona.src.sciona.reducers.helpers.utils`
- `sciona.src.sciona.reducers.metadata`

These are structurally critical and may represent architectural bottlenecks; changes here are inherently risky.  
telemetry evidence: `hotspot_summary`

---

**Potential Security-Relevant Issues (Moderate)**
1. **Git subprocess execution depends on caller‑supplied `cwd`.**  
`run_git_in_cwd(...)` validates arguments but does not validate `cwd`. If any caller passes user‑controlled paths, this allows git commands to run outside the intended repo boundary.  
Files and callables:
- `src/sciona/runtime/git/exec.py` — `sciona.src.sciona.runtime.git.exec.run_git_in_cwd`  
structural evidence: `callable_overview`  
source evidence: `callable_source`  
Recommendation: either validate `cwd` (e.g., require `.git` or configured repo root) or document that this is strictly internal with trusted inputs.

2. **Allowed git commands include filesystem‑touching modes.**  
`validate_git_args(...)` permits `hash-object --stdin-paths` and `ls-files --others/--exclude-standard/--stage/...`. These are safe for most internal use, but if arguments or `input_text` are derived from user input, this can be used to probe filesystem contents (existence/metadata via hashes or file listings).  
Files and callables:
- `src/sciona/runtime/git/exec.py` — `sciona.src.sciona.runtime.git.exec.validate_git_args`
- `src/sciona/runtime/git/exec.py` — `sciona.src.sciona.runtime.git.exec._run_git_raw`  
structural evidence: `callable_overview`  
source evidence: `callable_source`  
Recommendation: confirm call sites do not accept untrusted input, or tighten allowed options.

---

**Status (Strict Mode)**
Status: sciona used: yes | worktree: dirty | diff: unavailable | warned: yes  
Evidence:  
- structural: `structural_integrity_summary` (lexical orphans, integrity_ok=false)  
- telemetry: `hotspot_summary` (fan‑in/fan‑out hotspots)  
- source: `callable_source` for `run_git_in_cwd`, `validate_git_args`, `_run_git_raw`  
- overlay_advisory: `overlay_impact_summary` reports `overlay_available=false` (committed snapshot only)

I did not run tests.

If you want, I can:
1. Trace where the lexical orphans are introduced by running targeted reducers on those files.  
2. Map diff_overlay dependencies to determine the minimal refactor boundaries.  
3. Trace call sites of `run_git_in_cwd` and validate the trust boundary.