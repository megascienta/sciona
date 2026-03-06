## Model

- GPT-5.4-Codex Copilot / VS Code
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

- worked for 2m 49s

Status: sciona used: yes | worktree: dirty | diff: unavailable | warned: yes

Evidence: `snapshot_provenance` shows analysis against committed snapshot `0eb3af97a30fc1c3afcb399b88070db6956660f5`; `overlay_impact_summary` reports `overlay_available: false`, so structural findings are committed-snapshot only. `structural_integrity_summary` reports `integrity_ok: false` with 20 lexical orphans. `module_overview`, `file_outline`, and `dependency_edges` confirm the module/import relationships cited below. Non-structural security findings are labeled `non-SCIONA evidence: source scan`.

1. High: the documented read-only addon API is not actually read-only for `emit(...)`. The guide states that [`sciona.api.addons`](#/Users/dc/Calculations/sciona-suite/sciona/docs/DEVELOPERGUIDE.md#L113) is the “stable read-only addon surface” and that “addon access is read-only” at [docs/DEVELOPERGUIDE.md#L128](/Users/dc/Calculations/sciona-suite/sciona/docs/DEVELOPERGUIDE.md#L128). But [`src/sciona/api/addons.py`](#/Users/dc/Calculations/sciona-suite/sciona/src/sciona/api/addons.py#L12) re-exports `emit` from `pipelines.reducers`, and [`pipelines.reducers.emit`](#/Users/dc/Calculations/sciona-suite/sciona/src/sciona/pipelines/reducers.py#L68) opens CoreDB with `core(...)` and ArtifactDB with `artifact(...)`, both of which use writable `mode=rwc` connectors and schema-initializing paths in [`data_storage/connections.py`](#/Users/dc/Calculations/sciona-suite/sciona/src/sciona/data_storage/connections.py#L40). That is a contract breach and a security-relevant loss of defense-in-depth: third-party addon calls that are documented as read-only are executed with write-capable database handles.

2. High: the committed structural snapshot violates the lexical tree contract. [`docs/CONTRACT.md`](#/Users/dc/Calculations/sciona-suite/sciona/docs/CONTRACT.md#L75) requires every non-module structural node to have exactly one lexical parent. `structural_integrity_summary` reports 20 lexical orphans, including nested CLI handlers in [`src/sciona/cli/reducer.py`](#/Users/dc/Calculations/sciona-suite/sciona/src/sciona/cli/reducer.py#L36) and several `register_*` command files. `file_outline` for `src/sciona/cli/reducer.py` shows nested callables like `register.reducer`, `register.info_reducers`, and `register.list_reducers`, while the integrity reducer still flags them as orphans. This means reducer outputs are already violating the core structural contract for real repository code, which undermines any downstream reducer or policy that assumes a valid lexical tree.

3. Medium: the runtime layer reaches into code-analysis internals, contradicting the documented layer boundaries. The guide says [`src/sciona/runtime/`](#/Users/dc/Calculations/sciona-suite/sciona/docs/DEVELOPERGUIDE.md#L32) is for paths/identity/logging/git/errors and that dependency direction is downward-only at [docs/DEVELOPERGUIDE.md#L43](/Users/dc/Calculations/sciona-suite/sciona/docs/DEVELOPERGUIDE.md#L43). However [`src/sciona/runtime/agents_setup.py`](#/Users/dc/Calculations/sciona-suite/sciona/src/sciona/runtime/agents_setup.py#L11) imports `extensions_for_language` from `code_analysis.core.extract.registry`. `module_overview` and `dependency_edges` confirm that `sciona.src.sciona.runtime.agents_setup` imports `sciona.src.sciona.code_analysis.core.extract.registry`. This is a structural design leak from runtime into extraction internals, which makes the “runtime” layer depend on analysis implementation details and raises the risk of circular evolution pressure between unrelated layers.

4. Medium: `non-SCIONA evidence: source scan` shows the hook installer writes arbitrary shell commands verbatim into `.git/hooks/post-commit` with no validation. The CLI accepts `--command` in [`src/sciona/cli/commands/register_hooks.py`](#/Users/dc/Calculations/sciona-suite/sciona/src/sciona/cli/commands/register_hooks.py#L20), passes it through unchanged, and [`src/sciona/pipelines/hooks.py`](#/Users/dc/Calculations/sciona-suite/sciona/src/sciona/pipelines/hooks.py#L24) persists it directly into the hook body. If any higher-level caller ever forwards untrusted input here, this becomes persistent arbitrary command execution on every commit. Even if intended for trusted users, the lack of validation is a release-risky footgun.

No other clear critical security defect surfaced from the targeted scan. I did not run tests.