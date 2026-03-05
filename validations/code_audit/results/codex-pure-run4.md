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

- worked for 4m 44s
- explored 29 files, 21 searches, 2 lists

**Critical Misalignments With Documented Principles/Contracts**

1. **CALLS edges are not emitted into CoreDB.**
   - Contract says CALLS are structural edges and applies to the committed snapshot in CoreDB. Yet no analyzer emits `edge_type="CALLS"` and `StructuralAssembler.persist_analysis` only writes `analysis.edges` (lexical/imports/extends/implements) to CoreDB; `analysis.call_records` are never converted into CALLS edges.
   - Evidence: `src/sciona/code_analysis/core/structural_assembler.py` (method `persist_analysis` only emits `analysis.edges`), no CALLS emission in language analyzers under `src/sciona/code_analysis/languages/builtin/`.
   - Calls are instead persisted in ArtifactDB via `src/sciona/code_analysis/artifacts/rollups.py` and `src/sciona/data_storage/artifact_db/rollup_persistence.py`, which conflicts with the contract’s CoreDB scope.

**Structural Design Problems**

1. **Strict call gate is computed per-file with a per-file symbol/import index, creating inconsistent contract enforcement.**
   - `StructuralAssembler._normalize_call_records` builds `symbol_index`, `module_lookup`, and import targets solely from the current file’s `analysis.nodes`/`analysis.edges`. That means the strict gate cannot consider in-repo candidates outside the current file, which is required by the contract.
   - Even if this is currently used only for diagnostics, it creates contract-inconsistent behavior and makes the pipeline’s “strict gate” semantics depend on ingestion chunking.
   - Evidence: `src/sciona/code_analysis/core/structural_assembler.py` method `_normalize_call_records` and helpers in `src/sciona/code_analysis/core/structural_assembler_index.py`.

2. **Duplicated call-resolution pipelines with divergent logic.**
   - Core path: `_normalize_call_records` uses `select_strict_call_candidate` with a per-file index.
   - Artifact path: `_resolve_callees` re-resolves against the full snapshot and includes “rescue” steps like export-chain narrowing and TS barrel resolution.
   - This splits the definition of “strict call acceptance” across two implementations, risking inconsistent diagnostics and behavior across pipeline stages.
   - Evidence: `src/sciona/code_analysis/core/structural_assembler.py` vs `src/sciona/code_analysis/artifacts/rollups.py`.

**Potential Security-Relevant Issues**

1. **Symlink traversal allows reading files outside the repo.**
   - `FileSnapshot.content` reads bytes directly from `record.path` without verifying that the path is within the repo root and not a symlink. `walker.collect_files` accepts tracked paths and does not reject symlinks. A malicious repo could include symlinks to sensitive files outside the repo, and SCIONA would read them.
   - Evidence: `src/sciona/code_analysis/core/normalize/model.py` (`FileSnapshot.content`), `src/sciona/code_analysis/tools/walker.py`, `src/sciona/code_analysis/tools/snapshots.py`.

---

I did not run tests (not requested).

If you want, I can:
1. Propose a minimal, contract-aligned design for CALLS edges in CoreDB and a migration plan.
2. Implement a repo-bound, symlink-safe file access guard for `FileRecord`/`FileSnapshot`.
3. Consolidate strict call-gate logic to a single shared pipeline.