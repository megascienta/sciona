## Model

- GPT-5.2-Codex Copilot / VS Code

## Prompt

You are implementing multi-threaded parsing for SCIONA code_analysis layer. Current single thread execution must stay and remain the default. Introduce an optional multi-threaded parsing mode behind an option switch.

The solution must respect the architectural principles described in docs/DEVELOPERGUIDE.md, including SCI immutability, deterministic reducer outputs, stable structural identifiers, and ordering guarantees.

Requirements: parsing results (SCI / reducers) must remain deterministic; no changes in DS schemas; no changes to reducer contracts; no snapshot hash instability; no race conditions in CoreDB / ArtifactDB writes.

Analyse the codebase and propose a detailed implementation plan and concrete code-level modifications. Include a file-by-file list of proposed changes and any new files. Explicitly list potential issues and how you will avoid nondeterminism and DB races.

## Results

- worked for 3m 10s
- explored 24 files, 9 searches, 3 lists

Here’s a concrete, code-level implementation plan that keeps single-thread the default, adds an explicit opt-in switch, and preserves determinism, SCI immutability, and DB safety.

**Summary**
We’ll add a `analysis.parse_workers` config option (default `1`) and introduce a parallel parsing helper that runs analyzers concurrently but applies results sequentially in deterministic file order. All DB writes remain single-threaded. This preserves structural hashes, reducer outputs, and ordering guarantees.

**Implementation Plan**
1. Add analysis parsing settings to runtime config (`analysis.parse_workers`), defaulting to `1`.
2. Introduce a thread-safe parsing helper that:
   - Creates per-thread analyzer instances (no shared parser state).
   - Parses file snapshots in parallel.
   - Returns results in the same deterministic order as the input.
3. Update core ingestion (`BuildEngine`) to use the helper when `parse_workers > 1`.
4. Update artifact analysis (`ArtifactEngine`) to use the helper when `parse_workers > 1`.
5. Update diff overlay analysis (`pipelines/diff_overlay/compute.py`) to use the same helper, ensuring deterministic ordering of overlay payloads.
6. Add tests to validate determinism with `parse_workers > 1`.

**Proposed Code Changes (file-by-file)**
1. `src/sciona/runtime/config/models.py`
   - Add `AnalysisSettings` dataclass with `parse_workers: int`.
   - Add `analysis: AnalysisSettings` to `RuntimeConfig`.
2. `src/sciona/runtime/config/defaults.py`
   - Add `DEFAULT_ANALYSIS_PARSE_WORKERS = 1`.
3. `src/sciona/runtime/config/parse.py`
   - Add `_coerce_int`.
   - Add `_load_analysis_settings` parsing `analysis.parse_workers`.
   - Update `load_runtime_config` to include `analysis`.
4. `src/sciona/runtime/config/loaders.py`
   - Expose `runtime.analysis` via `load_runtime_config` and `load_sciona_config`.
5. `src/sciona/runtime/config/__init__.py`
   - Export `AnalysisSettings`.
6. `src/sciona/runtime/config/io.py`
   - Update `write_default_config` template to include:
     ```
     analysis:
       parse_workers: 1
     ```
7. New file `src/sciona/code_analysis/tools/parallel.py`
   - Provide `ThreadLocalAnalyzers` and `analyze_file_snapshots(...)`.
   - `analyze_file_snapshots` should:
     - Accept file snapshots and worker count.
     - Submit parse tasks via `ThreadPoolExecutor`.
     - Return a list of outcomes aligned to input order.
   - Outcomes should include: `file_snapshot`, `module_name`, `analysis` or `exception`, and a `skipped` flag.
8. `src/sciona/code_analysis/core/engine.py`
   - Load analysis settings (either via `runtime_config.load_runtime_config` or a new optional parameter).
   - If `parse_workers <= 1`, keep existing single-threaded loop unchanged.
   - If `parse_workers > 1`, use `analyze_file_snapshots` and then:
     - Iterate results in order.
     - For failures, emit warnings and `register_module_node` with `partial_parse`.
     - For successes, call `persist_analysis` sequentially.
9. `src/sciona/code_analysis/artifacts/engine.py`
   - Same approach: parallel parsing, then ordered accumulation of `call_records`.
   - Keep DB reads (`_load_node_map`) on main thread only.
10. `src/sciona/pipelines/diff_overlay/compute.py`
    - Use `analyze_file_snapshots` to build `nodes`, `edges`, `calls` in file order.
11. Tests
    - `tests/test_snapshot_determinism.py`
      - Add a new test case that sets `analysis.parse_workers: 4` and asserts `compute_structural_hash` matches the single-thread run.
    - `tests/test_artifact_engine.py`
      - Add a test validating call artifact output consistency with `parse_workers > 1`.

**Concrete Code-Level Notes**
- **Thread-local analyzers**: Use `threading.local()` to cache per-thread analyzers by language, so parsers are not shared across threads.
- **Outcome ordering**: Maintain a list indexed by the original file order; apply results in order to preserve deterministic ingestion.
- **No DB access in workers**: Workers only parse; `persist_analysis`, `register_module_node`, and any DB writes remain in the main thread.

**Potential Issues and Mitigations**
1. **Analyzer thread safety**
   - Risk: Tree-sitter parsers are not thread-safe.
   - Mitigation: Create one analyzer instance per thread; do not share analyzers or parsers across threads.
2. **SQLite connection safety**
   - Risk: SQLite connections are not thread-safe.
   - Mitigation: No DB calls in worker threads. All DB writes remain in the main thread.
3. **Nondeterministic ordering**
   - Risk: Parallel execution can reorder results.
   - Mitigation: Collect results and apply strictly in the deterministic file order already used by `walker.collect_files`.
4. **Snapshot hash instability**
   - Risk: Insertion order changes could affect structural hash.
   - Mitigation: Structural hash queries are already ordered by structural IDs and edge keys. Keeping deterministic file-order ingestion ensures stable intermediate state as well.
5. **Progress and warnings ordering**
   - Risk: Parallel execution could interleave outputs.
   - Mitigation: Only the main thread updates progress and emits warnings in file order.
6. **Analyzer module_name errors**
   - Risk: Exceptions in `module_name` should remain fatal like today.
   - Mitigation: Do not catch `module_name` exceptions in worker; let them propagate and fail the build, matching current behavior.

If you want, I can turn this plan into a patch set directly. If so, I’ll start by adding the config plumbing and the parallel parsing helper, then wire it into `BuildEngine`, `ArtifactEngine`, and diff overlay with tests.