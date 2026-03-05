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

- worked for 4m 18s
- explored 32 files, 22 searches, 11 lists

Below is the pre-release audit based on `docs/CONTRACT.md`, `docs/DEVELOPERGUIDE.md`, and `docs/CAPABILITY_MANIFEST.json`, plus a scan of the codebase.

**Critical Misalignments With Documented Principles/Contracts**
1. CALLS edges are effectively limited to same-file callables, which violates the contract’s in-repo CALLS requirement.  
   Evidence: `StructuralAssembler._normalize_call_records` builds a symbol index only from the current file’s `analysis.nodes`, then applies `select_strict_call_candidate` against that per-file index. `BuildEngine` processes files one at a time, so cross-file call targets cannot be accepted.  
   Files: `src/sciona/code_analysis/core/structural_assembler.py` (method `_normalize_call_records`), `src/sciona/code_analysis/core/structural_assembler_index.py` (`build_symbol_index`), `src/sciona/code_analysis/core/engine.py` (file-by-file ingestion).  
   Contract impact: `docs/CONTRACT.md` requires `CALLS` to represent syntactic call expressions to in-repo callables, not only same-file callables.

2. Deterministic ordering does not follow the contract’s required order.  
   Evidence: nodes are sorted by `(node_type, qualified_name)` in `StructuralAssembler.persist_analysis`, but the contract requires module path lexical order first, then qualified name.  
   Files: `src/sciona/code_analysis/core/structural_assembler.py` (`persist_analysis`).  
   Contract impact: `docs/CONTRACT.md` “Determinism” section.

**Structural Design Problems**
1. Call resolution logic is split across three layers, increasing drift risk and inconsistent diagnostics.  
   Evidence: adapters resolve call targets (`*_calls.py`), assembler re-applies strict candidate selection (`StructuralAssembler._normalize_call_records`), and artifacts re-resolve to build `CALL_SITES` (`code_analysis/artifacts/rollups.py:_resolve_callees`).  
   Files:  
   `src/sciona/code_analysis/languages/builtin/python/python_calls.py`  
   `src/sciona/code_analysis/languages/builtin/typescript/typescript_calls.py`  
   `src/sciona/code_analysis/languages/builtin/java/java_calls.py`  
   `src/sciona/code_analysis/core/structural_assembler.py`  
   `src/sciona/code_analysis/artifacts/rollups.py`  
   Risk: inconsistent acceptance logic and divergence between CALLS vs CALL_SITES diagnostics.

2. “Internal import” normalization depends on module_index derived only from the current discovery set.  
   Evidence: `BuildEngine` sets `analyzer.module_index` from `changed_snapshots` only, which can exclude modules via discovery globs or partial runs. Import normalization then treats some in-repo modules as external, affecting `IMPORTS_DECLARED` and subsequent resolution.  
   Files: `src/sciona/code_analysis/core/engine.py` (module_index construction), `src/sciona/code_analysis/languages/builtin/typescript/typescript_imports.py` (internal-module filtering), similar patterns in other import collectors.  
   Risk: non-deterministic edges based on discovery scope.

**Potential Security-Relevant Issues**
1. Symlink traversal can read files outside the repo during discovery and snapshotting.  
   Evidence: `walker.collect_files` accepts any tracked path, then constructs `abs_path = repo_root / rel_path` and reads the file without resolving or enforcing it stays under `repo_root`. `snapshots.prepare_file_snapshots` then opens these paths for line counting and blob hashing. A tracked symlink can point outside the repo, enabling unintended file reads.  
   Files: `src/sciona/code_analysis/tools/walker.py` (`collect_files`), `src/sciona/code_analysis/tools/snapshots.py` (`prepare_file_snapshots`).  
   Mitigation: resolve paths and ensure they remain under `repo_root`, or skip symlinks by default.

**Notes**
- I did not run tests. If you want, I can run `pytest -q` in the `multiphysics` conda env.

**Suggested Next Steps**
1. Decide how to fix CALLS resolution scope (global symbol index or defer strict gate until full snapshot) and I can implement it.  
2. Confirm whether contract-required ordering should be enforced at insertion time or via query ordering, then adjust `persist_analysis` accordingly.  
3. Add a repo-root containment check (and/or symlink exclusion) in discovery and snapshotting.