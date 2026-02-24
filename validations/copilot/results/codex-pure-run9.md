## Model

- GPT-5.2-Codex Copilot / VS Code

## Prompt

You are implementing multi-threaded parsing for SCIONA code_analysis layer. Current single thread execution must stay and remain the default. Introduce an optional multi-threaded parsing mode behind an option switch.

The solution must respect the architectural principles described in docs/DEVELOPERGUIDE.md, including SCI immutability, deterministic reducer outputs, stable structural identifiers, and ordering guarantees.

Requirements: parsing results (SCI / reducers) must remain deterministic; no changes in DS schemas; no changes to reducer contracts; no snapshot hash instability; no race conditions in CoreDB / ArtifactDB writes.

Analyse the codebase and propose a detailed implementation plan and concrete code-level modifications. Include a file-by-file list of proposed changes and any new files. Explicitly list potential issues and how you will avoid nondeterminism and DB races.

## Results

- worked for 2m 0s
- explored 21 files, 9 searches, 1 list

Below is a concrete plan that keeps single-threaded parsing as default, adds an opt‑in multi-threaded parsing mode, and preserves all invariants from `docs/DEVELOPERGUIDE.md`. I’m not changing any code yet—this is the requested design + file-by-file modification list with nondeterminism/race mitigation.

**Summary**
- Keep existing single-threaded path untouched as default.
- Add a new optional parsing setting in `.sciona/config.yaml` (under `analysis:`) to enable multi-threaded parsing and set worker count.
- Implement a parallel “analyze” phase that is fully read‑only and collects per‑file results in memory.
- Persist results to CoreDB strictly in deterministic order, in the main thread only.

**Proposed Config Shape (backward compatible)**
Add a new runtime analysis block to `.sciona/config.yaml`:

```yaml
analysis:
  parsing:
    mode: "single"   # "single" (default) or "multi"
    workers: 4       # ignored in single mode; default auto/CPU
```

Defaults preserve current behavior:
- mode defaults to `single` if missing.
- workers defaults to `0`/`None` meaning “auto” (e.g., `min(32, os.cpu_count() or 1)`), but only used when `mode: multi`.

**Implementation Plan**

1. **Config and policy plumbing**
   - Extend runtime config models to include parsing settings.
   - Parse the new `analysis.parsing` block in config parsing.
   - Carry parsing settings into `AnalysisPolicy` and into `BuildEngine`.

2. **Parallel analysis in `BuildEngine`**
   - Keep module registration exactly as today (single-threaded, before analysis).
   - Build a deterministic list of `FileSnapshot` entries (already sorted).
   - If parsing mode is `single`, keep current loop unchanged.
   - If parsing mode is `multi`:
     - Use `ThreadPoolExecutor`.
     - Each worker creates its own analyzer instance (no shared parser objects).
     - Worker does *only*:
       - `module_name = analyzer.module_name(...)`
       - `analysis = analyzer.analyze(...)`
       - Returns `(index, module_name, analysis, error)` where `index` is the position in `changed_snapshots`.
     - Main thread:
       - Collect results in a list indexed by file order.
       - For each index in order, either:
         - persist analysis via `StructuralAssembler.persist_analysis`, or
         - on error, call `register_module_node(..., metadata={"status": "partial_parse", "error": ...})`
       - This preserves deterministic ordering and prevents any DB races.

3. **Determinism guarantees**
   - Ordering is stable because persistence follows original snapshot order.
   - `structural_id` computation is deterministic and unaffected by parallel parsing.
   - Structural hash is based on ordered queries (`ORDER BY`) so even if insertion order differs, hash stays deterministic.
   - Warnings/parse failures are collected and emitted in file order (store per-index warnings and then append in order).

4. **Thread safety / DB safety**
   - No DB access in worker threads.
   - No shared `tree_sitter.Parser` instances between threads; each worker creates its own analyzer (and parser).
   - SQLite connection remains single-threaded in main thread.

**File-by-File Proposed Changes**

1. `src/sciona/runtime/config/models.py`
   - Add:
     - `@dataclass(frozen=True) class ParsingSettings: mode: str; workers: int`
     - `@dataclass(frozen=True) class AnalysisSettings: parsing: ParsingSettings`
   - Add `analysis: AnalysisSettings` to `RuntimeConfig`.
   - This is runtime config only—no schema changes.

2. `src/sciona/runtime/config/defaults.py`
   - Add defaults for parsing, e.g.:
     - `DEFAULT_PARSE_MODE = "single"`
     - `DEFAULT_PARSE_WORKERS = 0` (or `None` pattern if you prefer).
   - Keep existing defaults untouched.

3. `src/sciona/runtime/config/parse.py`
   - Add `_load_analysis_settings(...)` that:
     - Reads `analysis.parsing.mode` (accepts `"single"`/`"multi"`, else fallback to default).
     - Reads `analysis.parsing.workers` (coerce int, clamp to >=1 if mode is multi).
   - Include it in `load_runtime_config(...)`.
   - Validate strictly but default to single if invalid to avoid breaking existing configs.

4. `src/sciona/runtime/config/io.py`
   - Update `write_default_config(...)` to include the new `analysis` block with default `mode: single` and `workers` value.
   - Keep older sections unchanged to avoid breaking callers.

5. `src/sciona/pipelines/domain/policies.py`
   - Extend `AnalysisPolicy` to include `parsing: ParsingSettings` (or `AnalysisSettings`), in addition to `languages`.

6. `src/sciona/pipelines/policy/build.py`
   - Pass `runtime_cfg.analysis.parsing` into `AnalysisPolicy`.

7. `src/sciona/code_analysis/core/routing.py` or `src/sciona/code_analysis/core/extract/registry.py`
   - Add helper to get a **new** analyzer instance per request (or expose analyzer factory).
   - Example: `registry.get_analyzer_factory(language)` returning `AnalyzerFactory`.

8. `src/sciona/code_analysis/core/engine.py`
   - Add a new constructor param: `parsing_settings` or `analysis_settings` (from policy).
   - Add `_run_analysis_single(...)` (existing code path).
   - Add `_run_analysis_parallel(...)` with executor, per-thread analyzers, and deterministic result commit.
   - Ensure warnings and `parse_failures` are appended in file order.

9. **Optional new helper file**
   - `src/sciona/code_analysis/core/parallel.py` (optional):
     - Thread-local analyzer cache or small worker helper functions to keep `engine.py` readable.
   - If this feels like overkill, keep it in `engine.py`.

10. **Tests**
   - `tests/test_snapshot_determinism.py`
     - Add a test to run build/engine with parsing mode multi and compare structural hash to single mode.
   - `tests/test_engine_semantics.py`
     - Add a test to assert that when a worker throws, it still registers a module node (same as current behavior).
   - Tests must avoid real threading flakiness by using small input and deterministic analyzers (can use monkeypatch to force fast analyzers).

**Potential Issues and How We Avoid Them**

1. **Non‑deterministic ordering of warnings/errors**
   - Problem: futures complete in random order.
   - Fix: store warnings/errors keyed by file index and append in deterministic order.

2. **SQLite connection is not thread‑safe**
   - Problem: using `conn` in worker threads would break.
   - Fix: worker threads are strictly CPU/IO parsing only. All DB writes remain on main thread.

3. **Tree-sitter parser thread safety**
   - Problem: Parser objects are not thread-safe.
   - Fix: Each worker instantiates its own analyzer and parser. No shared parser instance.

4. **Structural cache race**
   - Problem: `StructuralAssembler.structural_cache` is not thread-safe.
   - Fix: Only used in main thread during persistence.

5. **Snapshot hash instability**
   - Problem: if persistence order changes and hash depends on DB read order.
   - Fix: hash uses `ORDER BY` queries; persisted content is deterministic. We also commit in file order to keep content stable.

6. **Reducer outputs / schema contracts**
   - Problem: changing node/edge semantics.
   - Fix: analysis outputs are unchanged; only execution strategy changes. No schema changes.

7. **Module registration order**
   - Problem: if modules were registered in a different order, could change structural nodes timing.
   - Fix: module registration remains the same sequential path before analysis.

**Notes on Default Behavior**
- No behavior change if `analysis.parsing.mode` is absent or `single`.
- Multi-threaded mode is entirely opt‑in.

If you want, I can move to implementing this plan. Suggested next steps:
1. Implement config + policy plumbing.
2. Add parallel analysis path in `BuildEngine`.
3. Add determinism tests for multi-thread mode.

Which step do you want first?