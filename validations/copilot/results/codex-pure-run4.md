## Model

- GPT-5.2-Codex Copilot / VS Code

## Prompt

You are implementing multi-threaded parsing for SCIONA code_analysis layer. Current single thread execution must stay and remain the default. Introduce an optional multi-threaded parsing mode behind an option switch.

The solution must respect the architectural principles described in docs/DEVELOPERGUIDE.md, including SCI immutability, deterministic reducer outputs, stable structural identifiers, and ordering guarantees.

Requirements: parsing results (SCI / reducers) must remain deterministic; no changes in DS schemas; no changes to reducer contracts; no snapshot hash instability; no race conditions in CoreDB / ArtifactDB writes.

Analyse the codebase and propose a detailed implementation plan and concrete code-level modifications. Include a file-by-file list of proposed changes and any new files. Explicitly list potential issues and how you will avoid nondeterminism and DB races.

## Results

- worked for 2m 3s
- explored 27 files, 5 searches, 2 lists

Below is a concrete, code-level plan based on the current architecture and invariants in `docs/DEVELOPERGUIDE.md`. I’m keeping the current single-threaded path as the default, and introducing a strictly optional multi-threaded parsing mode with deterministic persistence and no concurrent DB writes.

**Summary**
- Parallelize parsing only. Keep DB writes single-threaded and ordered.
- Introduce a parsing mode switch in `.sciona/config.yaml` with default `single`.
- Ensure deterministic outcomes by persisting analyses in the same deterministic file order as today.

**Implementation Plan**
1. Add runtime config for parsing concurrency.
2. Thread-safe analyzer instantiation per worker.
3. Parse in parallel, persist in a stable order on the main thread.
4. Apply the same approach to `ArtifactEngine` so call extraction stays deterministic.
5. Add tests to verify determinism and default behavior.

**File-by-File Proposed Changes**
1. `src/sciona/runtime/config/models.py`
- Add dataclasses:
  - `ParsingSettings` with `mode: str` and `workers: int`
  - `AnalysisSettings` with `parsing: ParsingSettings`
- Extend `RuntimeConfig` to include `analysis: AnalysisSettings`.

2. `src/sciona/runtime/config/defaults.py`
- Add defaults for parsing, e.g.:
  - `DEFAULT_PARSING_MODE = "single"`
  - `DEFAULT_PARSING_WORKERS = 0` (only used if `mode == "multi"`)

3. `src/sciona/runtime/config/parse.py`
- Parse `analysis.parsing` block from `.sciona/config.yaml`.
- If missing, default to `mode="single"` and `workers=0`.
- Validate `workers >= 0` and coerce invalid values to default.

4. `src/sciona/runtime/config/io.py`
- Update `write_default_config` to emit:
  - `analysis:`
  - `  parsing:`
  - `    mode: "single"`
  - `    workers: 0`

5. `src/sciona/runtime/config/loaders.py` and `src/sciona/runtime/config/__init__.py`
- Re-export new settings types if they’re used across layers.

6. `src/sciona/pipelines/domain/policies.py`
- Extend `AnalysisPolicy` to include parsing settings.

7. `src/sciona/pipelines/policy/build.py`
- Pass `runtime_cfg.analysis.parsing` into the `AnalysisPolicy`.

8. `src/sciona/code_analysis/core/engine.py`
- Add a deterministic parallel parsing path that:
  - Uses `ThreadPoolExecutor`.
  - Creates per-thread analyzer instances (no shared `Parser`).
  - Captures `analysis` or `exc` per file snapshot.
  - Persists results in original `changed_snapshots` order.
- Keep current sequential loop as the default path.

9. `src/sciona/code_analysis/artifacts/engine.py`
- Mirror the parallel parsing approach for call-record extraction only.
- Aggregate `call_records` in file-order, not completion order.

10. Tests (examples to extend)
- `tests/test_snapshot_determinism.py`
- `tests/test_engine_semantics.py`
- `tests/test_artifact_engine.py`
- Add coverage to assert that:
  - `single` and `multi` parsing produce identical CoreDB contents.
  - Default config remains single-threaded.

**Determinism and Race Avoidance**
- DB writes remain single-threaded inside the existing CoreDB transaction in `BuildEngine.run`. No CoreDB/ArtifactDB writes from worker threads.
- Persistence occurs in stable, deterministic order, exactly matching current single-thread file iteration.
- Structural IDs remain stable because `ids.structural_id(...)` is deterministic and DB writes happen in consistent order.
- No changes to schema or reducer contracts; reducers still consume the same SCI.
- Warnings and parse failure counts are built in file order to keep outputs stable.

**Potential Issues and Mitigations**
- Parser thread-safety: avoid sharing `Parser` instances. Each worker owns its own analyzer/Parser instance.
- Memory pressure from storing `AnalysisResult` for all files: limit worker count and optionally stream results with `executor.map` to avoid unbounded buffering.
- Progress reporting: update progress as futures complete, but keep warning aggregation and persistence strictly in file order.

**Open Decision**
- Switch location: config-only is simplest and preserves stability. If you want a CLI override like `sciona build --parsing-mode multi --parsing-workers N`, I can wire that through `pipelines/repo.py` and `register_build.py` without touching CoreDB behavior.

If you want me to implement this, I can proceed and include the tests.