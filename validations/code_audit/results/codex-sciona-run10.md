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

- worked for 2m 35s
- explored 6 files, 5 searches, 1 lists

**Findings**

**Critical Misalignments With Documented Principles/Contracts**
- Contract requires every non-`module` node to have exactly one lexical parent (`LEXICALLY_CONTAINS`), but the committed snapshot has 25 lexical orphans. This is a direct contract violation and can corrupt reducer outputs and call attribution. Examples of orphaned callables include:
  - `sciona.src.sciona.cli.commands.register_build.register_build.build` in `src/sciona/cli/commands/register_build.py`
  - `sciona.src.sciona.cli.commands.register_hooks.register_hooks.install` in `src/sciona/cli/commands/register_hooks.py`
  - `sciona.src.sciona.code_analysis.languages.builtin.python.python_resolution_instances.collect_callable_instance_map.walk` in `src/sciona/code_analysis/languages/builtin/python/python_resolution_instances.py`
  - `sciona.src.sciona.code_analysis.languages.builtin.typescript.typescript_node_walk.walk_typescript_nodes._emit_bound_callable` in `src/sciona/code_analysis/languages/builtin/typescript/typescript_node_walk.py`
  - `sciona.src.sciona.pipelines.diff_overlay.affection.scoped_affection._call_match` in `src/sciona/pipelines/diff_overlay/affection.py`
Evidence (structural): `structural_integrity_summary` reports `lexical_orphan_count = 25` with the specific qualified names and file paths.

**Structural Design Problems**
- **Extraction coverage risk**: 77 of 403 Python files are “low-node” (≤1 node), ~19.1% of Python files. While not a contract breach, it suggests large portions of Python sources may be effectively invisible to the structural model, increasing odds of blind spots in reducers and call graph analyses.
Evidence (telemetry): `structural_integrity_summary` low-node diagnostics for Python.

**Potential Security-Relevant Issues**
- `run_git_in_cwd` executes git commands in an arbitrary `cwd` without validating that the directory is a repo root (unlike `run_git`, which enforces `validate_repo_root`). If a caller passes an untrusted path, git will operate in that directory, potentially enabling unintended repository access or metadata reads. This is mitigated by the allowlist and lack of shell invocation, but it is still a boundary-relevant risk.
Evidence (source): `src/sciona/runtime/git/exec.py:146` shows `run_git_in_cwd` bypassing `validate_repo_root`.  
Cross-check anchor (structural): `file_outline` for `src/sciona/runtime/git/exec.py` confirms the callable structure.

---

**Status**: sciona used: yes | worktree: dirty | diff: unavailable | warned: yes  
Evidence: structural_integrity_summary (structural, telemetry); file_outline for `src/sciona/runtime/git/exec.py` (structural); `src/sciona/runtime/git/exec.py:146` (source)

---

If you want, I can go deeper on any of the orphaned areas (e.g., narrow down which parser/extractor stage introduces the orphan nodes) or perform a targeted security sweep of `src/sciona/runtime/` and `src/sciona/api/` with SCIONA-backed function references.