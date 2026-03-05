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

- worked for 1m 59s
- explored 2 files, 0 searches, 1 lists

Below is a focused pre-release audit based on the **latest committed SCIONA snapshot**. Your worktree is dirty and the diff overlay is unavailable, so findings may be stale relative to uncommitted changes.

**Critical misalignments with documented principles/contracts**

1. **Contract violation: lexical orphans exist.**  
   The contract requires every non-`module` structural node to have exactly one lexical parent; SCIONA reports `lexical_orphan_count: 25`, which violates that invariant. This is a direct misalignment with `docs/CONTRACT.md` (LEXICALLY_CONTAINS rules) and indicates structural extraction inconsistencies.  
   Examples reported as orphans include:  
   - `src/sciona/cli/commands/register_agents.py` → `sciona.src.sciona.cli.commands.register_agents.register_agents.agents`  
   - `src/sciona/cli/commands/register_build.py` → `sciona.src.sciona.cli.commands.register_build.register_build.build`  
   - `src/sciona/cli/commands/register_hooks.py` → `sciona.src.sciona.cli.commands.register_hooks.register_hooks.install`  
   Evidence label: `structural`.  
   Status: this alone makes `structural_integrity_summary.integrity_ok` false.

**Structural design problems**

1. **Structural integrity is reported as failing for the snapshot.**  
   The SCIONA integrity reducer reports `integrity_ok: false` due to lexical orphans. This is a structural health failure in the core model, not just a local anomaly. It undermines any consumer that assumes the lexical tree is complete (e.g., reducers, call attribution).  
   Evidence label: `structural`.

2. **Orphans concentrate in CLI and language-resolution helpers.**  
   The orphan list includes CLI registration functions and internal walkers (e.g., `python_resolution_instances.collect_*_map.walk`) which are expected to be nested callables. This pattern suggests a systematic mismatch between extraction rules for nested callables and SCIONA’s own structural contract, rather than isolated file defects.  
   Evidence label: `structural`.  
   Note: this is an inference from the orphan set, not a source-level diagnosis.

**Potential security-relevant issues**

1. **Git command execution accepts caller-provided args; safety depends on upstream trust.**  
   `src/sciona/runtime/git/exec.py` defines `run_git(...)` and `_run_git_raw(...)` that execute `subprocess.run([...])` using the caller’s `args` (validated but still caller-controlled). Validation does **not** permit arbitrary git commands, but it **does** allow `hash-object --stdin-paths` and allows argument lists after `--` (pathspecs). If any caller passes untrusted input into `run_git(...)`, this can be used to read paths for hashing or expand pathspecs within the repo.  
   - `run_git` → `sciona.src.sciona.runtime.git.exec.run_git`  
   - `_run_git_raw` → `sciona.src.sciona.runtime.git.exec._run_git_raw`  
   - `validate_git_args` → `sciona.src.sciona.runtime.git.exec.validate_git_args`  
   Evidence label: `source` with `structural` cross-check from `callable_overview`.

**Status (Strict Mode)**  
Status: sciona used: yes | worktree: dirty | diff: unavailable | warned: yes  
Evidence:  
- `snapshot_provenance` shows the committed snapshot and commit SHA used.  
- `structural_integrity_summary` reports `integrity_ok: false` and `lexical_orphan_count: 25` with concrete orphaned callables and file paths.  
- `file_outline`/`callable_overview`/`callable_source` used to anchor git execution callables and their implementation.

If you want me to go deeper on the orphan root cause or validate the git execution call sites, I need either a clean worktree or an explicit request to proceed with non-SCIONA inspection of dirty changes.

**Next steps (pick one)**  
1. Commit or stash current changes, then I’ll rerun SCIONA integrity checks to validate the orphan condition on a clean snapshot.  
2. Ask me to trace `run_git(...)` call sites via SCIONA to determine whether untrusted inputs can reach it.