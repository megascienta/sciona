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

- worked for 6m 38s
- explored 46 files, 26 searches, 4 lists

**Critical Misalignments**
1. `LEXICALLY_CONTAINS` span rule is violated. The contract forbids identical parent/child spans, but `_validate_lexical_containment` allows a module parent with an identical span to its child. This contradicts `CONTRACT.md`. File: `src/sciona/code_analysis/core/structural_assembler.py` in `_validate_lexical_containment`.
2. Deterministic ordering is wrong. The contract requires stable ordering by module path then qualified name, but `persist_analysis` sorts nodes by `(node_type, qualified_name)`. File: `src/sciona/code_analysis/core/structural_assembler.py` in `persist_analysis`.
3. `CALLS` edges are not emitted into CoreDB. Analyzers only produce `call_records`; `StructuralAssembler` never emits `CALLS` edges to core, and `CALLS` are merged into artifact `graph_edges` from `node_calls` instead. This conflicts with the structural edge requirements in `CONTRACT.md`. Files: `src/sciona/code_analysis/core/structural_assembler.py`, `src/sciona/code_analysis/core/structural_assembler_emit.py`, `src/sciona/data_storage/artifact_db/maintenance_graph.py`.
4. TypeScript/JavaScript relative import normalization can incorrectly treat out-of-repo relative paths as internal modules by clamping `..` above root. External/unresolved imports are out-of-contract, but this code can normalize them into internal module names. File: `src/sciona/code_analysis/languages/builtin/typescript/typescript_imports.py` in `normalize_relative_path` and `normalize_import` (also affects JS via `javascript_imports.py`).

**Structural Design Problems**
1. Dual strict-call gating with different symbol scopes. `StructuralAssembler._normalize_call_records` gates using only file-local symbols, while artifact rollups resolve with a repo-wide symbol index. This can yield inconsistent acceptance, diagnostics, and edge sets between core and artifact layers. Files: `src/sciona/code_analysis/core/structural_assembler.py`, `src/sciona/code_analysis/artifacts/rollups.py`.
2. Artifact call analysis re-runs analyzers on live files rather than using stored core snapshot outputs. This duplicates the analysis pipeline and risks drift if parsers or resolution logic change between core build and later artifact refresh. Files: `src/sciona/code_analysis/artifacts/engine.py`, `src/sciona/pipelines/build_artifacts.py`.

**Potential Security-Relevant Issues**
1. `blob_sha`/`blob_sha_batch` accept `relative_path` without enforcing repo-relative or no-`..` constraints. If any external caller supplies untrusted paths, `git hash-object` could read arbitrary filesystem paths relative to the repo root. Current internal callers use tracked paths, but the public API is permissive. File: `src/sciona/runtime/git/ops.py`.

Tests not run (not requested).

If you want, I can propose specific patches for the contract misalignments first (CALLS in CoreDB, ordering, and span rule), then tighten the TS/JS import normalization and git path validation.

Next steps:
1. Fix CoreDB `CALLS` emission and align artifact graph construction with it.
2. Adjust node ordering and containment validation to match `CONTRACT.md`.
3. Harden TS/JS relative import normalization for out-of-repo paths.