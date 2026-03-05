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

- worked for 5m 42s
- explored 42 files, 25 searches, 2 lists

**Summary**
I reviewed `docs/CONTRACT.md`, `docs/DEVELOPERGUIDE.md`, and `docs/CAPABILITY_MANIFEST.json`, then scanned the core analysis, language adapters, storage, and pipeline layers. Below are the findings grouped by the requested categories, with concrete file references.

**Critical Misalignments With Documented Principles or Contracts**
1. **`CALLS` edges are not emitted into CoreDB.**  
   The contract requires `CALLS` as a structural edge type. In core ingestion, `persist_analysis` only emits `analysis.edges`, and analyzers only add `CallRecord` entries (not `EdgeRecord` of type `CALLS`). There is no core write path that turns `CallRecord` into `CALLS` edges.  
   Files: `src/sciona/code_analysis/core/structural_assembler.py`, `src/sciona/code_analysis/core/structural_assembler_emit.py`, `src/sciona/code_analysis/core/extract/ir/extraction_buffer.py`, `src/sciona/code_analysis/languages/builtin/python/python.py`.

2. **Lexical containment allows identical parent/child spans for module parents, which conflicts with the contract.**  
   The contract states parent/child spans MUST NOT be identical. The current validator explicitly allows identical spans when the parent is a `module`, which violates the contract as written.  
   File: `src/sciona/code_analysis/core/structural_assembler.py` in `_validate_lexical_containment`.

3. **Deterministic ordering does not follow the contract’s required ordering.**  
   The contract requires ordering by module path lexical order then qualified name. Core assembly currently sorts nodes by `(node_type, qualified_name)` and the IR builder does not enforce any module-first ordering. This is a contract-level mismatch on output ordering.  
   Files: `src/sciona/code_analysis/core/structural_assembler.py` in `persist_analysis`, `src/sciona/code_analysis/core/extract/ir/ir_builder.py`.

**Structural Design Problems**
1. **Core call gate uses only per-file symbols/imports, which would drop cross-file calls if `CALLS` were emitted.**  
   `_normalize_call_records` builds its `symbol_index`, `module_lookup`, and `import_targets` from the current file’s `analysis.nodes`/`analysis.edges` only. That makes strict call acceptance effectively file-local. This is a structural correctness problem given the contract requires in-repo call edges (not just intra-file).  
   Files: `src/sciona/code_analysis/core/structural_assembler.py` in `_normalize_call_records`, `src/sciona/code_analysis/core/structural_assembler_index.py`.

2. **Call resolution work is duplicated and partially dead in core.**  
   Core build normalizes `CallRecord` data but does not persist it or emit `CALLS` edges. Artifact builds re-run analyzers to regenerate call data anyway. This is wasted compute and increases the chance of divergence between core and artifact paths.  
   Files: `src/sciona/code_analysis/core/structural_assembler.py`, `src/sciona/code_analysis/artifacts/engine.py`, `src/sciona/pipelines/build_artifacts.py`.

3. **Contract vs. implementation split of call graph responsibility is unclear.**  
   The contract declares `CALLS` as structural, but the implementation places call graph materialization in artifact rollups instead of CoreDB. This is a design-level mismatch that should be resolved either by updating the contract or moving `CALLS` emission into core.  
   Files: `docs/CONTRACT.md`, `src/sciona/code_analysis/artifacts/rollups.py`, `src/sciona/data_storage/artifact_db/rollup_persistence.py`.

**Potential Security-Relevant Issues**
1. **`clean_repo` deletes `.sciona` without a symlink safety check (TOCTOU risk).**  
   If `.sciona` is replaced with a symlink between validation and deletion, `shutil.rmtree` could remove paths outside the repo.  
   File: `src/sciona/pipelines/exec/repo.py` in `clean_repo`.

2. **Git path handling is newline-delimited and not `-z` safe.**  
   `tracked_paths` parses `git ls-files` output by splitting on newlines. Repositories containing filenames with newlines can cause path confusion in discovery and in later hashing (`blob_sha_batch` uses newline-delimited stdin). This can lead to incorrect file selection or unexpected reads.  
   File: `src/sciona/runtime/git/ops.py` in `tracked_paths` and `blob_sha_batch`.

3. **Hashing uses `git hash-object` over user-controlled paths (guarded but still sensitive).**  
   While arguments are validated and the paths are repo-relative, any future path source that is not strictly from `git ls-files` could allow hashing of unintended files. This is low severity today but worth tracking given it’s a low-level helper.  
   File: `src/sciona/runtime/git/ops.py` in `blob_sha` and `blob_sha_batch`, `src/sciona/runtime/git/exec.py` in `validate_git_args`.

**Notes**
- I did not run tests.
- No direct conflicts found between `docs/DEVELOPERGUIDE.md` and `docs/CONTRACT.md`, but the contract/implementation mismatch around `CALLS` is material.

If you want, I can propose concrete fixes for the `CALLS` emission path and the ordering mismatch.