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

- worked for 2m 6s
- explored 3 files, 0 searches, 1 lists

**Audit Summary (Pre-Release)**

Status: sciona used: yes | worktree: dirty | diff: unavailable | warned: yes  
Evidence: structural (file outlines, symbol lookup), telemetry (structural integrity, hotspots, call resolution quality), source (selected callable sources).  
Diff overlay: `_diff.overlay_available=false` in `overlay_impact_summary`; evidence reflects committed snapshot only.

---

**Critical Misalignments With Documented Contracts**

1. **Lexical containment contract violation (critical).**  
`docs/CONTRACT.md` requires every non-module structural node to have exactly one lexical parent (LEXICALLY_CONTAINS). The structural integrity reducer reports `integrity_ok=false` with `lexical_orphan_count=25`, which violates that contract. Examples include:  
`src/sciona/cli/commands/register_agents.py` callable `register_agents.agents`  
`src/sciona/cli/commands/register_build.py` callable `register_build.build`  
`src/sciona/cli/commands/register_hooks.py` callables `register_hooks.install`, `register_hooks.remove`, `register_hooks.status`  
`src/sciona/cli/commands/register_status.py` callables `register_status.clean`, `register_status.status`  
`src/sciona/cli/main.py` callable `_patch_click_make_metavar._make_metavar`  
`src/sciona/cli/reducer.py` callables `register._emit_reducer_info`, `register.info_reducers`, `register.list_reducers`, `register.reducer`  
`src/sciona/cli/resolve.py` callable `register.resolve`  
`src/sciona/cli/search.py` callable `register.search`  
`src/sciona/cli/utils.py` callable `agents_command_map._pick`  
`src/sciona/code_analysis/languages/builtin/python/python_imports.py` callable `collect_python_import_model._append_module`  
`src/sciona/code_analysis/languages/builtin/python/python_resolution_instances.py` callables `collect_callable_instance_map.walk`, `collect_callable_local_bindings.walk`, `collect_class_instance_map.walk`, `collect_module_instance_map.walk`  
`src/sciona/code_analysis/languages/builtin/typescript/typescript_node_walk.py` callable `walk_typescript_nodes._emit_bound_callable`  
`src/sciona/pipelines/diff_overlay/affection.py` callable `scoped_affection._call_match`  
Evidence label: `telemetry` (from `structural_integrity_summary`).

---

**Structural Design Problems**

1. **High fan-in/fan-out hotspots suggesting coupling pressure.**  
Modules with very high import fan-in (shared dependency choke points):  
`src/sciona/reducers/helpers/render.py`  
`src/sciona/code_analysis/core/normalize/model.py`  
`src/sciona/runtime/__init__.py`  
`src/sciona/reducers/helpers/utils.py`  
`src/sciona/reducers/metadata.py`  
Modules with very high import fan-out (broad dependency surface):  
`src/sciona/pipelines/diff_overlay/compute_core.py`  
`src/sciona/pipelines/diff_overlay/compute_config.py`  
`src/sciona/pipelines/diff_overlay/compute_payloads.py`  
`src/sciona/pipelines/diff_overlay/compute_summary.py`  
`src/sciona/pipelines/diff_overlay/ops_get.py`  
Evidence label: `telemetry` (from `hotspot_summary`).  
Risk: Changes in these modules are likely to ripple widely and complicate refactors or parallel development. It would be prudent to review whether some dependencies can be inverted or pushed to lower-level helpers.

2. **Call-resolution drop anomalies (minor structural risk).**  
`call_resolution_quality` shows 3 dropped callsites with reason `unique_without_provenance`. This isn’t a contract violation by itself but indicates that some callsites cannot be fully attributed/provenanced in the artifact layer, which can reduce analysis fidelity.  
Evidence label: `telemetry` (from `call_resolution_quality`).

---

**Potential Security-Relevant Issues**

1. **Git execution argument gating may allow unsafe positional arguments.**  
`src/sciona/runtime/git/exec.py`  
`validate_git_args` only restricts option flags for a small allowlist, but it allows arbitrary positional arguments after `--` without additional validation or normalization. Any caller that passes user-controlled input could supply pathspecs or other positional tokens to `git diff`, `git show`, `git ls-files`, etc. This is not an immediate exploit (no shell, args are list-based), but it does widen the allowed surface and can enable unintended data exposure or heavy workloads if callers are not careful.  
Evidence label: `source` (from `callable_source`) cross-checked by `file_outline` for callable existence.

2. **SQLite URI construction uses raw path string.**  
`src/sciona/data_storage/connections.py`  
`_base_connect` builds a SQLite URI with `f"file:{db_path.as_posix()}?mode={mode}"`. If `db_path` were ever influenced by untrusted input or contained `?`/`#`, it could inject extra URI parameters (e.g., `cache=shared`, `immutable=1`, etc.) altering connection behavior. If `db_path` is always internal and sanitized, this is low risk; otherwise it is worth escaping or using SQLite URI-safe encoding.  
Evidence label: `source` (from `callable_source`) cross-checked by `file_outline` for callable existence.

---

**Scope and Evidence Caveats**

- Worktree is dirty and diff overlay is unavailable, so all findings reflect the committed snapshot only.  
- I did not attempt a full layer-boundary import audit. The dependency edges sampled for `sciona.src.sciona.runtime` show only internal runtime imports, but this is not comprehensive across all layers.  
- No tests were run (audit only).

---

If you want, I can deepen any item by tracing callsites with `callsite_index` or validating layer boundaries with targeted `dependency_edges` queries.

Suggested next steps:
1. Decide if you want a full layer-boundary import audit across all top-level modules.  
2. Identify whether any public/CLI inputs feed into `run_git` or SQLite paths, then I can trace those call paths structurally.