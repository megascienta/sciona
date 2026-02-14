## Model

- GPT-5.2-Codex Copilot / VS Code

## Prompt

You are implementing multi-threaded parsing for SCIONA code_analysis layer. Current single thread execution must stay and remain the default. Introduce an optional multi-threaded parsing mode behind an option switch.

The solution must respect the architectural principles described in docs/DEVELOPERGUIDE.md, including SCI immutability, deterministic reducer outputs, stable structural identifiers, and ordering guarantees.

Requirements: parsing results (SCI / reducers) must remain deterministic; no changes in DS schemas; no changes to reducer contracts; no snapshot hash instability; no race conditions in CoreDB / ArtifactDB writes.

Analyse the codebase and propose a detailed implementation plan and concrete code-level modifications. Include a file-by-file list of proposed changes and any new files. Explicitly list potential issues and how you will avoid nondeterminism and DB races.

## Results

- worked for 2m 41s
- explored 21 files, 8 searches, 1 list

Got it. I analyzed the current build/analysis flow and where parsing happens. Below is a concrete, code-level plan that keeps single-threaded behavior as the default, adds an explicit opt‑in switch, and preserves determinism, snapshot hash stability, and DB safety.

**Summary**
I propose adding an `analysis.parsing` config block to `.sciona/config.yaml` (default `serial`), then introducing a shared parsing executor that can run analyzers concurrently but always persists results in stable, file-order on the main thread. This avoids DB races and preserves existing ordering semantics and structural hash stability.

**Implementation Plan**
1. Add parsing settings to runtime config with safe defaults.
2. Thread-safe parsing executor that returns results in original file order.
3. Wire BuildEngine to use threaded parsing only when enabled.
4. Wire ArtifactEngine and diff overlay analysis to use the same executor and config.
5. Update docs/config template and add targeted tests for config parsing and determinism.

**Proposed Config Switch**
Add to `.sciona/config.yaml`:
```yaml
analysis:
  parsing:
    mode: "serial"   # or "threaded"
    workers: 4       # only used when mode == "threaded"
```
Default remains serial. This is the explicit option switch.

**File-by-File Changes**

1. `src/sciona/runtime/config/models.py`
- Add `AnalysisSettings` dataclass and nested `ParsingSettings`.
- Extend `RuntimeConfig` to include `analysis: AnalysisSettings`.

2. `src/sciona/runtime/config/defaults.py`
- Add defaults: `DEFAULT_PARSING_MODE = "serial"`, `DEFAULT_PARSING_WORKERS = 0` (or 4 if you prefer explicit opt‑in still needing mode).

3. `src/sciona/runtime/config/parse.py`
- Add `_load_analysis_settings` that reads `analysis.parsing.mode` and `analysis.parsing.workers`.
- Export `load_analysis_settings(repo_root)` (similar to `load_language_settings`) for use in diff overlay.
- Update `load_runtime_config` to include `analysis=_load_analysis_settings(raw)`.

4. `src/sciona/runtime/config/__init__.py`
- Export `AnalysisSettings`, `ParsingSettings`, `load_analysis_settings`.

5. `src/sciona/runtime/config/io.py`
- Update `write_default_config` template to include the `analysis.parsing` block with serial defaults.

6. `src/sciona/pipelines/domain/policies.py`
- Extend `AnalysisPolicy` to include `parsing: AnalysisSettings` (or `ParsingSettings`).
- Update `__all__`.

7. `src/sciona/pipelines/policy/build.py`
- Pass parsing settings from `repo_state.config.runtime.analysis` into `AnalysisPolicy`.

8. `src/sciona/pipelines/exec/build.py`
- When instantiating `BuildEngine`, pass `analysis.parsing` (or `parse_workers` if you flatten it).

9. `src/sciona/code_analysis/core/engine.py`
- Add optional `parsing_settings` or `parse_workers` parameter to `BuildEngine`.
- Add a new parsing path:
  - Serial path remains current behavior.
  - Threaded path uses a shared executor (see new helper below) to parse in parallel but **persist in original file order**.
- Keep DB writes on the main thread only. No shared DB use in worker threads.

10. `src/sciona/code_analysis/artifacts/engine.py`
- Add parsing settings parameter.
- Use the same parallel parsing executor for call extraction.

11. `src/sciona/pipelines/diff_overlay/compute.py`
- Add `resolve_parsing_settings(repo_root)` with ConfigError fallback to defaults.
- Use the same parsing executor in `analyze_files`.

12. New helper file
- `src/sciona/code_analysis/tools/parallel_parse.py` (or `core/analysis_executor.py`)
- Responsibilities:
  - Threaded parse with `ThreadPoolExecutor`.
  - Thread-local analyzers (one per language per thread) to avoid tree-sitter parser sharing.
  - Returns results aligned to input order.
  - No DB access inside workers.

**Sketch of Executor Behavior**
- Input: ordered `file_snapshots`, `repo_root`, `languages`.
- For each file snapshot:
  - Worker builds analyzer via `registry.get_analyzer(language)` in thread‑local cache.
  - Computes `module_name`, calls `analyze`.
  - Returns `{file_snapshot, module_name, analysis, error}`.
- Main thread consumes results **in original order**:
  - On error: increment `parse_failures`, warn, register partial parse module node.
  - On success: `assembler.persist_analysis(...)` in order.

**Determinism & DB Safety: Risks and Mitigations**
1. **DB race conditions (CoreDB/ArtifactDB writes)**
- Risk: multi-threaded writes on shared sqlite connection.
- Mitigation: all DB writes remain on the main thread; worker threads do not touch DB.

2. **Non-deterministic node/edge presence due to file order**
- Risk: changing processing order affects `_lookup_structural_id` behavior for edges.
- Mitigation: preserve the original `file_snapshots` order when persisting. Parallel parse only changes how results are produced, not when they’re applied.

3. **Tree-sitter parser thread safety**
- Risk: parser instances are not thread-safe.
- Mitigation: create analyzers per thread via thread-local cache; never share parser instances across threads.

4. **Warning ordering and parse failure count**
- Risk: warnings emitted in completion order could become non-deterministic.
- Mitigation: record warnings and apply in file order when consuming ordered results.

5. **Snapshot hash instability**
- Risk: if persistence order changes, structural hash could change.
- Mitigation: persistence order is unchanged; `compute_structural_hash` already sorts by IDs.

6. **Reducer output stability**
- Risk: changes in SCI content order.
- Mitigation: no change in tables/fields or reducer contracts; deterministic insert order preserved.

**Tests to Add/Update**
1. Config parsing:
- New test: `analysis.parsing` block parses correctly and defaults to serial when absent.

2. Determinism smoke test:
- Run build twice with serial and with threaded enabled on the same repo, verify identical structural hash.

3. Artifact engine:
- Ensure call extraction count and content are identical between serial and threaded mode.

**Open Question**
Do you want the switch to be *config-only*, or also exposed as a CLI flag for `sciona build` (e.g. `--parsing threaded --workers 8`)? Config-only is simpler and preserves CLI stability.

If you want, I can proceed to implement this plan.