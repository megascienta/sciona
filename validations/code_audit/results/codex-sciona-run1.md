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

- worked for 2m 29s
- explored 6 files, 7 searches, 1 lists

Below is a pre‑release code audit based on the committed SCIONA snapshot. The worktree is dirty and SCIONA overlay data is unavailable, so findings may miss uncommitted changes.

**Critical Misalignments With Documented Principles/Contracts**
1. **Lexical parent contract violation (structural integrity failure).** The contract requires every non‑`module` structural node to have exactly one lexical parent and the lexical graph to be acyclic. The structural integrity reducer reports `lexical_orphan_count = 25`, which implies at least 25 structural nodes without a lexical parent. Examples include callables in `src/sciona/cli/commands/register_agents.py` (`sciona.src.sciona.cli.commands.register_agents.register_agents.agents`) and `src/sciona/cli/commands/register_status.py` (`...register_status.clean` and `...register_status.status`). This is a direct contract misalignment and should be treated as release‑blocking until resolved. Evidence: telemetry (structural_integrity_summary).  
   Affected examples:  
   - `src/sciona/cli/commands/register_agents.py`  
   - `src/sciona/cli/commands/register_build.py`  
   - `src/sciona/cli/commands/register_hooks.py`  
   - `src/sciona/cli/commands/register_init.py`  
   - `src/sciona/cli/commands/register_status.py`  
   - `src/sciona/cli/main.py`  
   - `src/sciona/cli/reducer.py`  
   - `src/sciona/cli/render.py`  
   - `src/sciona/cli/resolve.py`  
   - `src/sciona/cli/search.py`  
   - `src/sciona/cli/utils.py`  

**Structural Design Problems**
1. **High fan‑out orchestration module suggests over‑coupling.** `src/sciona/pipelines/diff_overlay/compute_core.py` imports at least 25 internal modules spanning `runtime`, `code_analysis`, `data_storage`, and other pipeline components. This concentration of dependencies suggests orchestration and core logic are tightly coupled in a single module, which raises change‑risk and makes testing isolation harder. Evidence: structural (dependency_edges for `sciona.src.sciona.pipelines.diff_overlay.compute_core`) and telemetry (hotspot_summary fan‑out).  
2. **High fan‑in utility modules indicate potential bottlenecks.** Modules such as `sciona.src.sciona.reducers.helpers.render`, `sciona.src.sciona.code_analysis.core.normalize.model`, and `sciona.src.sciona.runtime` are among the highest fan‑in modules. This suggests broad coupling where many modules depend on these utilities; refactors in these areas are likely high‑risk. Evidence: telemetry (hotspot_summary fan‑in).  

**Potential Security‑Relevant Issues**
1. **Unbounded git timeout from environment.** In `src/sciona/runtime/git/exec.py`, `resolve_git_timeout` uses `SCIONA_GIT_TIMEOUT` without an upper bound. A malicious environment could set an extreme value, increasing the risk of long‑running git operations and DoS‑style hangs. Consider clamping to a max. Evidence: source (file content) with structural cross‑check (file_outline for `sciona.src.sciona.runtime.git.exec.resolve_git_timeout`).  
2. **Config rewriter lacks size guard.** In `src/sciona/pipelines/exec/init_dialog.py`, `apply_language_selection` reads `.sciona/config.yaml` without the size guard present in `load_raw_config` (which enforces 1 MB). If a repo contains a very large config file, this code path can force large reads in an interactive init flow. Low severity, but it is a DoS‑style risk surface. Evidence: source (file content) with structural cross‑check (file_outline for `sciona.src.sciona.pipelines.exec.init_dialog.apply_language_selection`).  

**Status**
Status: sciona used: yes | worktree: dirty | diff: unavailable | warned: yes  
Evidence:  
- structural: `dependency_edges` for `sciona.src.sciona.pipelines.diff_overlay.compute_core`; file outlines for `src/sciona/runtime/git/exec.py` and `src/sciona/pipelines/exec/init_dialog.py`  
- telemetry: `structural_integrity_summary`, `hotspot_summary`  
- source: `src/sciona/runtime/git/exec.py`, `src/sciona/pipelines/exec/init_dialog.py`  
Diff overlay: unavailable; evidence is committed‑snapshot only.

If you want, I can continue by tracing the lexical orphan sources to the exact structural extraction steps and propose fixes. Possible next steps:  
1. Run a focused SCIONA reducer pass to locate and diagnose the specific orphaned nodes’ lexical parents.  
2. Propose a refactor plan for `compute_core` to reduce fan‑out, with concrete module split suggestions.  
3. Implement the two low‑severity security hardenings and run `pytest -q` in `conda` env `multiphysics`.