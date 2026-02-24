## Model

- GPT-5.2-Codex Copilot / VS Code

## Prompt

You are implementing multi-threaded parsing for SCIONA code_analysis layer. Current single thread execution must stay and remain the default. Introduce an optional multi-threaded parsing mode behind an option switch.

The solution must respect the architectural principles described in docs/DEVELOPERGUIDE.md, including SCI immutability, deterministic reducer outputs, stable structural identifiers, and ordering guarantees.

Requirements: parsing results (SCI / reducers) must remain deterministic; no changes in DS schemas; no changes to reducer contracts; no snapshot hash instability; no race conditions in CoreDB / ArtifactDB writes.

Analyse the codebase and propose a detailed implementation plan and concrete code-level modifications. Include a file-by-file list of proposed changes and any new files. Explicitly list potential issues and how you will avoid nondeterminism and DB races.

## Results

- worked for 2m 46s
- explored 22 files, 4 searches, 1 list

Below is a concrete, code-level implementation plan that preserves all invariants (SCI immutability, deterministic outputs, stable identifiers, ordering, and no DB races), while adding an **optional** multi‑threaded parsing mode (default remains single‑thread).

**High-level approach**
- Keep all **DB writes on the main thread** and in deterministic file order.
- Allow parsing to run in a worker pool **only when explicitly enabled** via config.
- Ensure **per‑thread analyzers** (Tree‑sitter parser instances are not shared).

---

**Plan**

1. **Add a runtime config switch for parsing parallelism**  
   Introduce `analysis.parse_workers` (int) in `.sciona/config.yaml`.
   - Default: `1` (single-thread, current behavior).
   - Any value `>1` enables multi-threaded parsing.

2. **Add a deterministic parallel parsing helper**  
   Create a helper that:
   - Accepts an ordered list of `FileSnapshot` objects.
   - Uses `ThreadPoolExecutor` only when `parse_workers > 1`.
   - Instantiates a **fresh analyzer per task** (`registry.get_analyzer(language)`), avoiding shared parsers.
   - Returns results in **exact input order**.
   - On errors, returns a structured failure record (no DB access inside workers).

3. **Integrate in `BuildEngine`**  
   - Keep `_register_modules()` as-is (single-thread).
   - Use the helper to parse files.
   - Persist results **sequentially in file order**, preserving deterministic insertion.
   - Keep existing warning semantics and partial-parse module node behavior.

4. **Integrate in `ArtifactEngine`**  
   - Same helper for analysis stage.
   - Collect call records in deterministic file order.

5. **(Optional but recommended) Integrate for diff overlays**  
   `pipelines/diff_overlay/compute.analyze_files()` is another analysis path; keep default single-thread but allow optional `parse_workers` (loaded from config in callers).

6. **Add/extend tests**  
   - New determinism test that compares **single-thread vs multi-thread** results on the same repo.
   - Ensure `compute_structural_hash` and committed snapshot ID remain identical.

---

**File-by-file change list**

1. `src/sciona/runtime/config/models.py`  
   - Add `AnalysisSettings` dataclass (e.g., `parse_workers: int`).
   - Extend `RuntimeConfig` to include `analysis: AnalysisSettings`.

2. `src/sciona/runtime/config/defaults.py`  
   - Add `DEFAULT_PARSE_WORKERS = 1`.

3. `src/sciona/runtime/config/parse.py`  
   - Add `_load_analysis_settings()` parsing `analysis.parse_workers` (int).
   - Ensure `parse_workers <= 1` coerces to `1`.

4. `src/sciona/runtime/config/io.py`  
   - Update default config template to include:
     ```
     analysis:
       parse_workers: 1
     ```

5. `src/sciona/runtime/config/loaders.py`  
   - Ensure `load_runtime_config()` returns the new analysis settings.
   - Optional: add `load_analysis_settings()` helper.

6. `src/sciona/code_analysis/tools/parallel_parse.py` (new)  
   - Implements `parse_file_snapshots(...) -> list[ParseOutcome]`.
   - Uses `ThreadPoolExecutor` only when enabled.
   - Preserves order via index tracking.

7. `src/sciona/code_analysis/tools/__init__.py`  
   - Export the new helper.

8. `src/sciona/code_analysis/core/engine.py`  
   - Load `analysis.parse_workers` (from runtime config or passed in).
   - Replace inline parse loop with helper.
   - Persist results sequentially.

9. `src/sciona/code_analysis/artifacts/engine.py`  
   - Same helper integration for analysis.
   - Preserve deterministic aggregation order for call records.

10. `src/sciona/pipelines/exec/build.py`  
    - Pass analysis settings into `BuildEngine`, or rely on `BuildEngine` to load from `config_root`.

11. `src/sciona/pipelines/diff_overlay/compute.py`  
    - Optional: accept `parse_workers` in `analyze_files()` and use helper.

12. Tests  
    - `tests/test_snapshot_determinism.py`: add a test path with `parse_workers > 1` and assert identical structural hash and committed snapshot ID.
    - If needed, add a small test to confirm deterministic call extraction order in `ArtifactEngine`.

---

**Determinism and race‑avoidance guarantees**

- **No DB races**:  
  All CoreDB/ArtifactDB writes stay on the main thread and in a single transaction. Workers only parse and return results.

- **Stable ordering**:  
  Input file list is already sorted by tracked paths (`walker.collect_files`). The helper guarantees results are **emitted in the same order**, so inserts happen exactly as in single-thread mode.

- **Stable structural IDs and hashes**:  
  Structural IDs are derived from `(node_type, language, qualified_name)` and written sequentially. Structural hashes are computed with DB ordering (`ORDER BY`), so insertion order remains irrelevant.

- **No reducer or schema changes**:  
  All outputs and DB schemas remain unchanged.

---

**Potential issues and mitigations**

1. **Tree-sitter parser thread-safety**  
   - Issue: parsers are not safe to share.  
   - Mitigation: **create a fresh analyzer per worker** (per task or per thread).

2. **Non-deterministic warning order**  
   - Issue: warnings could become completion-order dependent.  
   - Mitigation: store warnings per file and emit them **in input order** during sequential persistence.

3. **Memory pressure when storing parse results**  
   - Issue: large repos could yield large in-memory result lists.  
   - Mitigation: the helper can store results by index and flush in order as soon as the next index is available (bounded queue). This preserves determinism while limiting memory.

4. **Accidental multi-thread enablement**  
   - Issue: users might assume config default changes behavior.  
   - Mitigation: default `parse_workers: 1`; no change unless explicit.

---

If you want, I can follow this plan and implement it. Suggested next steps:

1. Confirm the config shape you prefer: `analysis.parse_workers` vs a boolean + worker count.  
2. Decide whether diff overlay analysis should also honor the same setting.