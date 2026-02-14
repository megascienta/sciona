## Model

- GPT-5.2-Codex Copilot / VS Code

## Prompt

You are implementing multi-threaded parsing for SCIONA code_analysis layer. Current single thread execution must stay and remain the default. Introduce an optional multi-threaded parsing mode behind an option switch.

The solution must respect the architectural principles described in docs/DEVELOPERGUIDE.md, including SCI immutability, deterministic reducer outputs, stable structural identifiers, and ordering guarantees.

Requirements: parsing results (SCI / reducers) must remain deterministic; no changes in DS schemas; no changes to reducer contracts; no snapshot hash instability; no race conditions in CoreDB / ArtifactDB writes.

Analyse the codebase and propose a detailed implementation plan and concrete code-level modifications. Include a file-by-file list of proposed changes and any new files. Explicitly list potential issues and how you will avoid nondeterminism and DB races.

## Results

- worked for 3m 18s
- explored 25 files, 6 searches, 1 list

Here’s a concrete, code-aware plan that keeps single‑thread parsing as the default, adds an explicit opt‑in switch, and preserves all determinism and DB safety guarantees.

**Summary**
- Add a runtime config switch for parsing mode (`single` default, `multi` optional) plus a worker count.
- Parallelize only the parsing/analysis phase with per‑thread analyzer instances.
- Keep all CoreDB/ArtifactDB writes single‑threaded and ordered exactly as today.
- Preserve deterministic ordering by processing results in input order (even if workers finish out of order).

**Plan**
1. Add parsing settings to runtime config models and YAML template with safe defaults (`single`, `workers: 0` meaning auto or `1`).
2. Thread‑safe, deterministic analysis helper in code_analysis that can run sequential or via `ThreadPoolExecutor` while returning results in the original file order.
3. Integrate helper into `BuildEngine` (core SCI ingest) and `ArtifactEngine` (call artifacts), without changing DB schemas or reducer contracts.
4. Optionally integrate into diff overlay parsing to keep consistent behavior (still read‑only and deterministic).
5. Add tests to assert single vs multi produce identical structural hash and call artifacts, plus config parsing defaults.

**File-by-File Proposed Changes**
- `src/sciona/runtime/config/models.py`  
  Add a new `ParsingSettings` dataclass and include it in `RuntimeConfig`. Keep existing fields unchanged.
- `src/sciona/runtime/config/defaults.py`  
  Add defaults like `DEFAULT_PARSE_MODE = "single"` and `DEFAULT_PARSE_WORKERS = 0`.
- `src/sciona/runtime/config/parse.py`  
  Add `_load_parsing_settings()` with validation (`mode in {"single","multi"}` and `workers >= 1` or `0` for auto). Wire into `load_runtime_config`.
- `src/sciona/runtime/config/io.py`  
  Extend `write_default_config()` template to include a `parsing:` block.
- `src/sciona/runtime/config/loaders.py` and `src/sciona/runtime/config/__init__.py`  
  Export/load parsing settings as part of runtime config.
- `src/sciona/pipelines/domain/policies.py`  
  Extend `AnalysisPolicy` to include parsing settings.
- `src/sciona/pipelines/policy/build.py`  
  Pass parsing settings from `repo_state.config.runtime` into `AnalysisPolicy`.
- `src/sciona/code_analysis/tools/` (new file, e.g. `analysis_workers.py`)  
  Add deterministic analysis helper:
  - Per‑thread analyzer cache via `threading.local()`.
  - `analyze_file_snapshots(...)` that returns a list of outcomes in the same order as input.
  - Supports sequential path when parsing mode is `single`.
- `src/sciona/code_analysis/core/engine.py`  
  Use the helper to parse files. Persist nodes/edges in input order only. Keep DB writes in the main thread. Preserve current warning/parse_failure semantics.
- `src/sciona/code_analysis/artifacts/engine.py`  
  Use the same helper, preserving order for call extraction aggregation.
- `src/sciona/pipelines/diff_overlay/compute.py` (optional but consistent)  
  Use helper for `analyze_files()` so overlay analysis respects the parsing mode while maintaining deterministic ordering.
- `docs/DEVELOPERGUIDE.md`  
  Add a short note under configuration about `parsing.mode` and determinism guarantees.

**Potential Issues and How We Avoid Nondeterminism / DB Races**
- Tree‑sitter parser thread safety  
  Mitigation: instantiate analyzers per thread; do not share parser instances between threads.
- Nondeterministic ordering of analysis results  
  Mitigation: collect results in input order (`executor.map` preserves order), then sequentially persist; warnings and parse_failures are emitted in the same deterministic order as today.
- CoreDB / ArtifactDB races  
  Mitigation: all DB writes and reads remain on the main thread with the existing transaction. Worker threads only parse and build in‑memory `AnalysisResult`.
- Snapshot hash instability  
  Mitigation: structural hash depends on DB contents with deterministic ordering queries; we keep insertion order stable and data identical.
- Reducer contract drift  
  Mitigation: no schema changes, no changes to node/edge semantics, no changes in reducer inputs or ordering contracts.

**Suggested Tests**
- `tests/test_snapshot_determinism.py`  
  Add a variant that runs `BuildEngine` with parsing mode `single` and `multi` on the same repo and asserts identical structural hash.
- `tests/test_artifact_engine.py`  
  Assert call artifacts are identical across modes.
- `tests/test_runtime_config.py` (new or existing config tests)  
  Verify parsing defaults are `single` and do not error if `parsing` block is missing.

If you want, I can turn this into a concrete patch next. Suggested next steps:
1. Confirm the config shape you want (`parsing:` at top level vs nested under `analysis:`).
2. Confirm whether `diff_overlay` should also honor the parsing mode.