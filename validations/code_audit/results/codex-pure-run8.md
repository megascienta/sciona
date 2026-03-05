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

- worked for 4m 56s
- explored 45 files, 12 searches, 5 lists

**Critical Misalignments**
1. **Lexical containment span invariant is relaxed for module parents.**  
   `docs/CONTRACT.md` requires parent/child spans for `LEXICALLY_CONTAINS` to be non‑identical. `StructuralAssembler._validate_lexical_containment` explicitly allows identical spans when the parent is a module, which violates the contract.  
   Files: `src/sciona/code_analysis/core/structural_assembler.py`

2. **CALLS emission is effectively limited to same‑file callables.**  
   The contract expects strict candidate selection after language‑specific resolution and import/module scoping. In `StructuralAssembler._normalize_call_records`, the symbol index used to validate candidates is built **only from the current file’s nodes** (`build_symbol_index(analysis.nodes)`), so any call resolved to a callable in another module is dropped during strict gating. This undermines import/module‑scoped resolution and likely violates cross‑file CALLS expectations implied by the contract and capability manifest.  
   Files: `src/sciona/code_analysis/core/structural_assembler.py`, `src/sciona/code_analysis/core/structural_assembler_index.py`

**Structural Design Problems**
1. **Divergent call resolution pipelines between CoreDB CALLS and ArtifactDB call_sites.**  
   Core CALLS are gated per file, while artifact rollups use a snapshot‑wide symbol index and additional rescue logic (Python export chains, TS barrel exports). This guarantees mismatched results: call_sites can show accepted candidates that never appear as CALLS edges, and resolution stats will not align with CoreDB. This creates inconsistent observable behavior across layers and makes debugging/analytics unreliable.  
   Files: `src/sciona/code_analysis/core/structural_assembler.py`, `src/sciona/code_analysis/artifacts/rollups.py`

**Potential Security‑Relevant Issues**
1. **Addon API “read‑only” guarantee is violated by write‑capable DB connections.**  
   The Developer Guide says addon access is read‑only, but `sciona.api.addons.emit` delegates to `pipelines.reducers.emit`, which opens **read‑write** CoreDB and ArtifactDB connections and passes them to reducers. This allows any addon or reducer to mutate the database, violating the documented contract and creating a privilege‑escalation path in plugin contexts.  
   Files: `src/sciona/api/addons.py`, `src/sciona/pipelines/reducers.py`, `src/sciona/data_storage/connections.py`

**Notes**
- Tests not run (per audit request).

If you want, I can propose a minimal patch plan to fix the misalignments (particularly cross‑file CALLS resolution and addon read‑only enforcement).