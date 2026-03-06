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

**Findings**  
No confirmed critical contract misalignments surfaced in the committed snapshot, but two issues require follow‑up:

1. **Potential contract breach: lexical orphans.** The contract requires every non‑module structural node to have exactly one lexical parent, and the lexical graph must be acyclic. The SCIONA integrity summary reports `lexical_orphan_count = 50`, which would violate that requirement if accurate. One flagged example is `register_agents.agents` in [register_agents.py](/Users/dc/Calculations/sciona-suite/sciona/src/sciona/cli/commands/register_agents.py#L14). This is reported as a structural integrity anomaly, not yet validated as a confirmed violation.  
2. **Layering direction concern.** The Developer Guide states dependency direction is downward only across layers. SCIONA shows `sciona.src.sciona.runtime.agents_setup` importing `sciona.src.sciona.code_analysis.core.extract.registry`. That is a runtime→code_analysis dependency, which appears upward if runtime is intended as a lower layer. The import is visible in [agents_setup.py](/Users/dc/Calculations/sciona-suite/sciona/src/sciona/runtime/agents_setup.py#L11). If the layer ordering is as listed in the guide, this should be treated as a structural design violation; if not, the guide needs clarification.

**Structural Design Problems**  
The diff overlay pipeline modules are structural hotspots with high import fan‑out (e.g., `pipelines.diff_overlay.compute_core`, `compute_config`, `compute_payloads`, `compute_summary`, `ops_get`). This is a maintainability risk and makes the diff overlay subsystem more fragile to change. No direct contract violation is implied, but the coupling is high.

**Security‑Relevant Issues**  
No high‑risk primitives such as `eval`, `exec`, unsafe YAML load, or pickle usage were found. The only subprocess usage is a constrained git wrapper. The helper uses `subprocess.run` without `shell=True`, validates allowed git commands/options, and enforces timeouts.  
`non-SCIONA evidence: source scan` in [exec.py](/Users/dc/Calculations/sciona-suite/sciona/src/sciona/runtime/git/exec.py#L47).  
If this wrapper is ever called with attacker‑controlled paths, consider whether git config hooks or external helpers could be triggered; I did not find a direct exploit path in the current scan.

**Status**  
Status: sciona used: yes | worktree: dirty (untracked file) | diff: unavailable (overlay unavailable) | warned: yes  
Evidence: `snapshot_provenance`, `structural_index`, `structural_integrity_summary` (lexical orphans), `dependency_edges` (runtime→code_analysis import), `module_overview` (runtime.agents_setup, code_analysis.core.extract.registry), `file_outline` and `symbol_lookup` (register_agents.agents), `callsite_index` (relations context), `hotspot_summary` (fan‑out hotspots).

Tests not run (audit only).