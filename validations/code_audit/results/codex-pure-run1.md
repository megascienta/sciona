## Model

- GPT-5.2-Codex Copilot / VS Code

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

- worked for 6m 34s
- explored 42 files, 29 searches, 4 lists

**Critical Misalignments (Contracts / Developer Guide)**  
- Addon API is documented as read-only, but `sciona.api.addons.emit` can write to the ArtifactDB when the worktree is dirty. The “stable, read-only” addon surface in [addons.py](/Users/dc/Calculations/sciona-suite/sciona/src/sciona/api/addons.py#L1) exports `emit` from [reducers.py](/Users/dc/Calculations/sciona-suite/sciona/src/sciona/pipelines/reducers.py#L69), which opens a read-write ArtifactDB connection and invokes diff overlay logic. `diff_overlay.get_overlay` writes overlay rows and commits to the ArtifactDB. This violates “addon access is read-only” in `docs/DEVELOPERGUIDE.md`.  
  Evidence: [reducers.py](/Users/dc/Calculations/sciona-suite/sciona/src/sciona/pipelines/reducers.py#L69), [ops_get.py](/Users/dc/Calculations/sciona-suite/sciona/src/sciona/pipelines/diff_overlay/ops_get.py#L114)

**Structural Design Problems**  
- Strict CALLS gate logic is duplicated and diverges between core and artifact pipelines. Core normalization in `StructuralAssembler._normalize_call_records` applies strict selection without any rescue/ambiguity heuristics. Artifact rollups add Python export-chain and TypeScript barrel rescues, and then record “accepted” callsites with a provenance label not used in core CALLS. This can produce callsite diagnostics that imply accepted targets that will never appear in CoreDB CALLS edges, weakening the invariant that CALLS is the single structural truth.  
  Evidence: [structural_assembler.py](/Users/dc/Calculations/sciona-suite/sciona/src/sciona/code_analysis/core/structural_assembler.py#L176), [rollups.py](/Users/dc/Calculations/sciona-suite/sciona/src/sciona/code_analysis/artifacts/rollups.py#L470)

**Potential Security-Relevant Issues**  
- Addon API write access (same as the misalignment above) is security-relevant: third‑party addons using the “read-only” API can mutate ArtifactDB state via diff overlays, which can persist data and influence downstream reporting. This undermines trust boundaries for addons and creates a write vector that is undocumented.  
  Evidence: [addons.py](/Users/dc/Calculations/sciona-suite/sciona/src/sciona/api/addons.py#L1), [reducers.py](/Users/dc/Calculations/sciona-suite/sciona/src/sciona/pipelines/reducers.py#L69), [ops_get.py](/Users/dc/Calculations/sciona-suite/sciona/src/sciona/pipelines/diff_overlay/ops_get.py#L114)

**Notes**  
- I did not run tests.  
- If you want, I can propose concrete fixes for the addon read-only contract breach and the callsite/core gate divergence.

**Next Steps (optional)**  
1. Fix addon read-only contract (e.g., route `emit` through a read-only artifact connection or disable overlay writes in addon context).  
2. Decide whether callsite rescue logic should be mirrored in core CALLS emission or constrained to “dropped” diagnostics only.