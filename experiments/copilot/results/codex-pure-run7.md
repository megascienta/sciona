## Model

- GPT-5.2-Codex Copilot / VS Code

## Prompt

You are implementing multi-threaded parsing for SCIONA code_analysis layer. Current single thread execution must stay and remain the default. Introduce an optional multi-threaded parsing mode behind an option switch.

The solution must respect the architectural principles described in docs/DEVELOPERGUIDE.md, including SCI immutability, deterministic reducer outputs, stable structural identifiers, and ordering guarantees.

Requirements: parsing results (SCI / reducers) must remain deterministic; no changes in DS schemas; no changes to reducer contracts; no snapshot hash instability; no race conditions in CoreDB / ArtifactDB writes.

Analyse the codebase and propose a detailed implementation plan and concrete code-level modifications. Include a file-by-file list of proposed changes and any new files. Explicitly list potential issues and how you will avoid nondeterminism and DB races.

## Results

- worked for 3m 41s
- explored 37 files, 8 searches, 1 list

Below is a concrete, code-aware plan that keeps single-threaded parsing as the default, adds an explicit switch for multi-threaded parsing, and preserves determinism and DB safety. I’ll reference the actual files and flows in this repo so the changes are actionable.

**Summary Of Current Flow**
- Core parsing is single-threaded in `BuildEngine.run()` (`src/sciona/code_analysis/core/engine.py`).
- Artifact call extraction is single-threaded in `ArtifactEngine.run()` (`src/sciona/code_analysis/artifacts/engine.py`).
- Dirty-worktree overlay analysis is single-threaded in `analyze_files()` (`src/sciona/pipelines/diff_overlay/compute.py`).
- DB writes happen only on the main thread in core build; artifact DB writes happen after parsing in `build_artifacts_for_snapshot()`.

---

**Proposed Switch + Behavior**
- Add a runtime config setting `analysis.parse_workers` in `.sciona/config.yaml`.
- Default: `1` (single-threaded, unchanged behavior).
- If `parse_workers > 1`, use a thread pool to parse files in parallel.
- **Crucial**: only parsing happens in threads. DB writes, snapshot decisions, and structural hash ingestion stay single-threaded and deterministic.

---

**Design Principles To Preserve Determinism**
1. **No DB writes in worker threads.** SQLite connections aren’t thread-safe in this context; DB writes remain on the main thread inside the existing transaction.
2. **Deterministic ordering of results.** Even with parallel parsing, results are collected and persisted in the same order as the input `FileSnapshot` list (which is already deterministic via sorted tracked paths).
3. **Per-thread analyzers.** Tree-sitter `Parser` is not thread-safe. Each worker must have its own analyzer instance (thread-local cache).
4. **Stable call artifacts.** Even if parse completion order differs, call records are merged in stable file order before writing.

---

**File-By-File Proposed Changes**

1. **`src/sciona/runtime/config/models.py`**
   - Add a new dataclass:
     - `AnalysisSettings(parse_workers: int)`
   - Add `analysis: AnalysisSettings` to `RuntimeConfig`.

2. **`src/sciona/runtime/config/defaults.py`**
   - Add `DEFAULT_PARSE_WORKERS = 1`.

3. **`src/sciona/runtime/config/parse.py`**
   - Add `_load_analysis_settings()`:
     - Reads `analysis.parse_workers`.
     - Coerces to `int`.
     - Clamps to `>= 1`.
   - Include the new settings in `load_runtime_config()`.

4. **`src/sciona/runtime/config/io.py`**
   - Update `write_default_config()` to include:
     ```
     analysis:
       parse_workers: 1
     ```

5. **`src/sciona/runtime/config/__init__.py`**
   - Export `AnalysisSettings`.

6. **`src/sciona/pipelines/domain/policies.py`**
   - Extend `AnalysisPolicy` with `parse_workers: int`.

7. **`src/sciona/pipelines/policy/build.py`**
   - Populate `AnalysisPolicy(parse_workers=runtime_cfg.analysis.parse_workers)`.

8. **`src/sciona/pipelines/exec/build.py`**
   - Pass `parse_workers` to `BuildEngine`.

9. **`src/sciona/code_analysis/core/engine.py`**
   - Add `parse_workers: int = 1` to `BuildEngine.__init__`.
   - Implement a parallel path in `run()`:
     - Keep `_register_modules()` as-is (main thread).
     - Use `ThreadPoolExecutor(max_workers=parse_workers)` when `parse_workers > 1`.
     - Parse each `FileSnapshot` in a worker:
       - Create analyzer instance via thread-local cache.
       - Compute `module_name`, run `analyzer.analyze()`.
     - Collect outcomes in a list keyed by input index.
     - Persist results sequentially in input order using existing `StructuralAssembler`.
   - Keep current single-thread path unchanged when `parse_workers <= 1`.

10. **`src/sciona/code_analysis/artifacts/engine.py`**
    - Add `parse_workers: int = 1`.
    - Use the same parallel parsing approach to gather `analysis.call_records`.
    - Merge results in input order, then proceed as today.

11. **`src/sciona/pipelines/build_artifacts.py`**
    - Pass `parse_workers` to `ArtifactEngine` (likely from `BuildPolicy.analysis.parse_workers`).

12. **`src/sciona/pipelines/diff_overlay/compute.py`**
    - Update `analyze_files()` to optionally accept `parse_workers`.
    - Use the same thread-local analyzer approach.
    - Preserve deterministic output order by processing results by input index.

---

**Minimal New Helper (Optional but Clean)**
Add a small internal helper to avoid analyzer reuse across threads:

- **New file**: `src/sciona/code_analysis/core/analyzer_provider.py`
  - Thread-local analyzer cache per language.
  - Uses `LANGUAGE_CONFIG[language].analyzer_factory`.
  - Provides `get_for_language(language: str)`.

This avoids sharing analyzers across threads and keeps thread-safety obvious.

---

**Potential Issues + How We Avoid Them**

1. **Tree-sitter parser thread-safety**
   - Risk: shared analyzer instances across threads can corrupt parse state.
   - Fix: per-thread analyzer instances (thread-local cache).

2. **SQLite connection threading**
   - Risk: concurrent writes lead to DB errors or races.
   - Fix: worker threads never touch DB; main thread performs all writes in deterministic order.

3. **Non-deterministic ordering of nodes/edges/calls**
   - Risk: futures complete in different order.
   - Fix: store outcomes by input index; persist sequentially. Input order is deterministic (tracked paths sorted).

4. **Call artifact instability**
   - Risk: if call records are merged by completion order, you could change which record “wins.”
   - Fix: merge in stable file order; only one record per caller anyway, but preserve order to be safe.

5. **Progress reporting in parallel**
   - Risk: progress updates from multiple threads could be unsafe.
   - Fix: only update progress in main thread when futures complete.

---

**Tests To Add/Adjust**
- `tests/test_snapshot_determinism.py`
  - Add a variant that sets `analysis.parse_workers: 4` and asserts identical structural hash.
- `tests/test_artifact_engine.py`
  - Add a run with `parse_workers > 1` to ensure it completes and returns a list.
- Any tests that write `.sciona/config.yaml` should include the new `analysis` block (or rely on defaults).

---

**Expected Behavior**
- Default behavior unchanged (single-threaded).
- With `analysis.parse_workers > 1`:
  - Parsing is parallelized.
  - DB writes and structural hashing remain deterministic.
  - Reducer outputs, SCI schema, and snapshot hashes remain stable.
  - No change to storage schema or reducer contracts.

---

If you want, I can follow up with a concrete patch sequence or draft the minimal helper class and the parallel parsing block in `BuildEngine.run()` so you can quickly review the implementation details.