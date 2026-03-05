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

- worked for 2m 19s
- explored 11 files, 6 searches, 1 lists

**Summary**
I used SCIONA for structural evidence and inspected targeted source files for contract/security checks. The committed snapshot shows **structural integrity failures** (lexical orphans), which is a direct contract violation. Several modules are structural hotspots with high fan-in/out, indicating tight coupling. I found two **potential security-relevant** risks around hook command injection and git execution in arbitrary directories.

**Findings**

1. **Critical contract misalignment: lexical orphans in committed snapshot**
- Contract requirement: every non-`module` node must have exactly one lexical parent (`LEXICALLY_CONTAINS`). `docs/CONTRACT.md`
- SCIONA reports `lexical_orphan_count: 50` and `integrity_ok: false`. This is a hard contract violation.
- Examples of orphans (from SCIONA structural evidence):
  - `src/sciona/cli/commands/register_agents.py` callable `register_agents.agents`
  - `src/sciona/cli/commands/register_build.py` callable `register_build.build`
  - `src/sciona/cli/commands/register_hooks.py` callables `register_hooks.install`, `register_hooks.remove`, `register_hooks.status`
  - `src/sciona/cli/commands/register_init.py` callable `register_init.init`
  - `src/sciona/cli/commands/register_status.py` callables `register_status.clean`, `register_status.status`
  - Additional orphans in `src/sciona/cli/main.py`, `src/sciona/cli/reducer.py`, `src/sciona/cli/render.py`, `src/sciona/cli/resolve.py`, `src/sciona/cli/search.py`, `src/sciona/cli/utils.py`, `src/sciona/code_analysis/languages/builtin/python/python_imports.py`, `src/sciona/code_analysis/languages/builtin/python/python_resolution_instances.py`, `src/sciona/code_analysis/languages/builtin/typescript/typescript_node_walk.py`, `src/sciona/pipelines/diff_overlay/*`, `src/sciona/pipelines/progress.py`, `src/sciona/reducers/analytics/hotspot_summary.py`, and several tests.  
- Impact: This violates the core structural contract and will undermine reducer correctness and any downstream tooling that relies on lexical containment.

Evidence label: `structural`

2. **Structural design hotspots indicating coupling risks**
- SCIONA hotspot telemetry shows high fan-in/out concentrations:
  - High fan-in modules: `sciona.src.sciona.reducers.helpers.render` (36), `sciona.src.sciona.code_analysis.core.normalize.model` (35), `sciona.src.sciona.runtime` (34), `sciona.src.sciona.reducers.helpers.utils` (32), `sciona.src.sciona.reducers.metadata` (32).
  - High fan-out modules: `sciona.src.sciona.pipelines.diff_overlay.compute_core` (25), `compute_config` (21), `compute_payloads` (21), `compute_summary` (21), `ops_get` (18).
- Risk: High fan-in modules become change bottlenecks; high fan-out diff-overlay modules are tightly coupled to many dependencies, making refactors risky and increasing regression surface.

Evidence label: `telemetry`

3. **Potential security-relevant: hook command injection surface**
- `src/sciona/cli/commands/register_hooks.py` allows `--command` to be passed from CLI.
- That `command` is injected verbatim into `.git/hooks/post-commit` in `src/sciona/pipelines/hooks.py` (`install_post_commit_hook` → `_render_block`).
- If any untrusted input can reach `--command` (e.g., wrapper scripts, plugins, or UI), this becomes arbitrary command execution on `git commit`. It’s an expected power-user feature, but still a security-relevant surface without guardrails.

Evidence label: `source`

4. **Potential security-relevant: git execution in arbitrary `cwd`**
- `src/sciona/runtime/git/exec.py` exposes `run_git_in_cwd(...)` which validates args but does not validate that `cwd` is a repo root.
- If `cwd` is user-controlled, Git may traverse parent directories or use environment overrides, which can lead to operations in unintended repositories or data exposure.

Evidence label: `source`

**Status**
Status: sciona used: yes | worktree: dirty | diff: unavailable | warned: yes  
Evidence: structural integrity summary shows lexical orphans and integrity failure; hotspot summary shows high fan-in/out modules; overlay summary indicates overlay unavailable for dirty worktree.

**Notes**
- Worktree is dirty and overlay is unavailable, so SCIONA evidence is committed-snapshot only. If uncommitted changes touch structural code, re-run with a clean commit and `sciona build` for authoritative results.

**Next steps I can take**
1. Triage the lexical orphan list and trace why `LEXICALLY_CONTAINS` edges are missing (likely extractor or assembler regression).  
2. Validate whether `run_git_in_cwd` is reachable from untrusted contexts and, if so, propose a constrained API or repo-root validation.