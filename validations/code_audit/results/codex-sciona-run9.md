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

- worked for 1m 50s
- explored 4 files, 2 searches, 1 lists

**Critical Misalignments**
1. **Contract violation: lexical parent requirement is broken (structural).**  
`docs/CONTRACT.md` requires every non-`module` node to have exactly one lexical parent, and the lexical graph must be acyclic. The `structural_integrity_summary` reducer reports `integrity_ok: false` with **25 lexical orphans** in the committed snapshot. This is a direct contract violation.  
Affected callables (examples; full set in evidence):  
- `sciona.src.sciona.cli.commands.register_agents.register_agents.agents` in `src/sciona/cli/commands/register_agents.py`  
- `sciona.src.sciona.cli.commands.register_build.register_build.build` in `src/sciona/cli/commands/register_build.py`  
- `sciona.src.sciona.cli.commands.register_hooks.register_hooks.install` in `src/sciona/cli/commands/register_hooks.py`  
- `sciona.src.sciona.cli.main._patch_click_make_metavar._make_metavar` in `src/sciona/cli/main.py`  
- `sciona.src.sciona.code_analysis.languages.builtin.python.python_resolution_instances.collect_callable_instance_map.walk` in `src/sciona/code_analysis/languages/builtin/python/python_resolution_instances.py`  
- `sciona.src.sciona.code_analysis.languages.builtin.typescript.typescript_node_walk.walk_typescript_nodes._emit_bound_callable` in `src/sciona/code_analysis/languages/builtin/typescript/typescript_node_walk.py`  
This contradicts the contract’s lexical containment guarantees and can corrupt reducer outputs and downstream reasoning.

**Structural Design Problems**
1. **Structural integrity is explicitly failing (structural).**  
The snapshot has `integrity_ok: false` with `lexical_orphan_count: 25`. This indicates the structural model is internally inconsistent, which undermines any reducer-driven reasoning or analysis fidelity.

2. **Evidence gap from dirty worktree with no overlay (overlay_advisory).**  
Worktree is dirty and `overlay_impact_summary` reports `overlay_available: false`, so evidence is committed-only and may be stale relative to current working files. That limits audit confidence for uncommitted changes and should be addressed before release.

**Potential Security‑Relevant Issues**
1. **Git subprocess inherits full environment (source).**  
`_run_git_raw` in `src/sciona/runtime/git/exec.py` uses `subprocess.run(...)` without supplying a controlled `env` and therefore inherits the full process environment. If callers allow untrusted environment variables (e.g., `GIT_DIR`, `GIT_WORK_TREE`, `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_SYSTEM`), git behavior can be influenced in unexpected ways. This is a common hardening gap for tools that operate on user‑supplied repositories.  
Relevant callables:  
- `sciona.src.sciona.runtime.git.exec._run_git_raw`  
- `sciona.src.sciona.runtime.git.exec.run_git`  
- `sciona.src.sciona.runtime.git.exec.run_git_in_cwd`  
- `sciona.src.sciona.runtime.git.exec.validate_git_args`

I didn’t find any direct use of `eval`, `exec`, or insecure deserialization in the scanned runtime area.

**Status**  
Status: sciona used: yes | worktree: dirty | diff: unavailable | warned: yes

**Evidence (structural)**  
- `structural_integrity_summary` reports `integrity_ok: false` and 25 lexical orphans, listing exact qualified names and file paths.  
- `symbol_lookup` resolves `run_git`, `_run_git_raw`, `run_git_in_cwd`, and `validate_git_args` to `src/sciona/runtime/git/exec.py`.  

**Evidence (overlay_advisory)**  
- `overlay_impact_summary` reports `overlay_available: false` for the dirty worktree.

---

If you want, I can dig into the specific lexical orphan sources to determine whether the extraction logic or IR assembly is failing, and propose concrete fixes.

Possible next steps:
1. Run `sciona build --force` after committing or stashing audit outputs to get a clean snapshot and recheck structural integrity.  
2. Add git environment hardening in `_run_git_raw` by sanitizing `env` for known `GIT_*` variables if untrusted inputs are expected.