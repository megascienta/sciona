## Model

- GPT-5.2-Codex Copilot / VS Code

## Prompt

You are implementing multi-threaded parsing for SCIONA code_analysis layer. Current single thread execution must stay and remain the default. Introduce an optional multi-threaded parsing mode behind an option switch.

The solution must respect the architectural principles described in docs/DEVELOPERGUIDE.md, including SCI immutability, deterministic reducer outputs, stable structural identifiers, and ordering guarantees.

Requirements: parsing results (SCI / reducers) must remain deterministic; no changes in DS schemas; no changes to reducer contracts; no snapshot hash instability; no race conditions in CoreDB / ArtifactDB writes.

Analyse the codebase and propose a detailed implementation plan and concrete code-level modifications. Include a file-by-file list of proposed changes and any new files. Explicitly list potential issues and how you will avoid nondeterminism and DB races.

## Results

- worked for 3m 3s
- explored 24 files, 6 searches, 1 list

**Summary**
I can add an optional multi-threaded parsing path in the code_analysis layer while keeping single-threaded as the default. The design preserves determinism by separating parallel parsing from serial persistence, ordering results by the original file list, and keeping all CoreDB/ArtifactDB writes on the main thread.

**Plan**
1. Introduce an `analysis` runtime config block with a `parse_workers` integer (default `1`) as the option switch. Values `<=1` keep current single-thread behavior.
2. Add a small analysis execution helper that can run analyzers in a `ThreadPoolExecutor` and return per-file results keyed by index.
3. Update `BuildEngine` and `ArtifactEngine` to use the helper when `parse_workers > 1`, but persist results in stable file order on the main thread.
4. Keep all DB writes single-threaded and inside existing transaction boundaries.
5. Add deterministic aggregation for warnings, parse_failures, and call artifacts.

**Proposed Code-Level Changes**
- Add `AnalysisSettings` to runtime config models and parsing.
- Add an analysis execution helper (new file) for parallel per-file parsing with per-task analyzer instances.
- Update `BuildEngine` to:
  - Determine `parse_workers` from config (or explicit parameter).
  - If `parse_workers > 1`, parse in parallel, then persist results in the original `file_snapshots` order.
  - Maintain warning order and parse failure count deterministically.
- Update `ArtifactEngine` to:
  - Use the same parallel helper.
  - Aggregate `call_records` in stable file order before mapping to `node_map`.
- Update `.sciona/config.yaml` template to include the new `analysis` block.
- Optionally update policy objects to pass `AnalysisSettings` through `BuildPolicy` rather than reloading runtime config inside engines.

**File-by-File Change List**
1. `src/sciona/runtime/config/models.py`
   - Add `@dataclass(frozen=True) class AnalysisSettings: parse_workers: int`.
   - Add `analysis: AnalysisSettings` field to `RuntimeConfig`.
2. `src/sciona/runtime/config/defaults.py`
   - Add `DEFAULT_PARSE_WORKERS = 1`.
3. `src/sciona/runtime/config/parse.py`
   - Parse `analysis.parse_workers` with coercion and minimum `1`.
   - Include `analysis` in `RuntimeConfig`.
4. `src/sciona/runtime/config/io.py`
   - Update `write_default_config` to emit:
     ```
     analysis:
       parse_workers: 1
     ```
5. `src/sciona/pipelines/domain/policies.py`
   - Extend `AnalysisPolicy` to include `analysis_settings: AnalysisSettings` (optional but cleaner).
6. `src/sciona/pipelines/policy/build.py`
   - Pass `runtime_cfg.analysis` into `AnalysisPolicy`.
7. `src/sciona/code_analysis/tools/analysis_executor.py` (new file)
   - Helper function like `run_analysis_jobs(file_snapshots, repo_root, parse_workers)` that:
     - Creates a `ThreadPoolExecutor(max_workers=parse_workers)`.
     - For each file, instantiates a fresh analyzer for that language via `registry.get_analyzer`.
     - Returns a list of result objects ordered by original index:
       - `success=True` with `AnalysisResult`, `module_name`.
       - `success=False` with exception for warnings.
8. `src/sciona/code_analysis/core/engine.py`
   - Accept `analysis_settings` or `parse_workers` in `__init__`.
   - If `parse_workers <= 1`, keep existing loop unchanged.
   - If `parse_workers > 1`, call the executor helper and then:
     - Iterate results by index in file order.
     - On success, call `persist_analysis` as today.
     - On failure, append warning, increment `parse_failures`, and call `register_module_node` with `metadata={"status": "partial_parse", "error": ...}`.
     - Keep progress updates in a deterministic loop (advance in order).
9. `src/sciona/code_analysis/artifacts/engine.py`
   - Same pattern as BuildEngine:
     - Parallel parse -> ordered aggregation -> map to `node_map`.
     - Preserve deterministic order of `call_records`.

**Potential Issues and How to Avoid Them**
- Thread-unsafe analyzers or parsers
  - Mitigation: create a new analyzer instance per task. Do not share analyzer instances across threads.
- Nondeterministic output ordering
  - Mitigation: always persist results in the original `file_snapshots` order. Use index-stable aggregation for warnings and call records.
- DB race conditions
  - Mitigation: keep all CoreDB/ArtifactDB writes in the main thread; worker threads only parse and return results.
- Snapshot hash instability
  - Mitigation: structural hash depends on ordered DB queries, not insertion order. By serializing persistence in a stable order, output remains identical.
- Progress reporting out of order
  - Mitigation: update progress in the same ordered loop used for persistence, not in `as_completed` order.
- Excessive concurrency on small repos
  - Mitigation: clamp `parse_workers` to `min(configured, len(file_snapshots))`.

**Optional Tests to Add**
- Deterministic snapshot hash for same repo with `parse_workers=1` and `parse_workers=4`.
- BuildEngine warnings order stability with forced parse failures.
- ArtifactEngine `call_artifacts` equality across different worker counts.

If you want, I can proceed with the concrete implementation next.