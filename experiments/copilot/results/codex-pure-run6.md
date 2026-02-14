## Model

- GPT-5.2-Codex Copilot / VS Code

## Prompt

You are implementing multi-threaded parsing for SCIONA code_analysis layer. Current single thread execution must stay and remain the default. Introduce an optional multi-threaded parsing mode behind an option switch.

The solution must respect the architectural principles described in docs/DEVELOPERGUIDE.md, including SCI immutability, deterministic reducer outputs, stable structural identifiers, and ordering guarantees.

Requirements: parsing results (SCI / reducers) must remain deterministic; no changes in DS schemas; no changes to reducer contracts; no snapshot hash instability; no race conditions in CoreDB / ArtifactDB writes.

Analyse the codebase and propose a detailed implementation plan and concrete code-level modifications. Include a file-by-file list of proposed changes and any new files. Explicitly list potential issues and how you will avoid nondeterminism and DB races.

## Results

- worked for 2m 39s
- explored 24 files, 4 searches, 3 lists

Below is a concrete, code-aware plan that stays within your invariants (SCI immutability, deterministic reducers, stable IDs, ordering guarantees, no DB races). I’m not changing schemas or reducer contracts, and the single-threaded path remains the default.

**Summary**
Introduce a configurable parsing worker count (default `1`) and only parallelize the **analysis phase**. All CoreDB writes and ordering-sensitive steps remain single-threaded and deterministic.

**Implementation Plan (High Level)**
1. Add runtime config for parsing workers (`analysis.parsing.workers`, default `1`).
2. Thread the setting through policy → build pipeline → `BuildEngine`.
3. In `BuildEngine`, parallelize **only** file parsing/AST analysis. Persist results in deterministic, original file order on the main thread.
4. Add tests to ensure multi-threaded mode yields the same structural output and error handling semantics.

---

**File-by-File Proposed Changes**

1. `src/sciona/runtime/config/models.py`  
   - Add:
     ```python
     @dataclass(frozen=True)
     class AnalysisSettings:
         parsing_workers: int
     ```
   - Update `RuntimeConfig` to include `analysis: AnalysisSettings`.

2. `src/sciona/runtime/config/defaults.py`  
   - Add `DEFAULT_PARSING_WORKERS = 1`.

3. `src/sciona/runtime/config/parse.py`  
   - Add `_load_analysis_settings(raw: Dict[str, Any]) -> AnalysisSettings`.
   - Parse `analysis.parsing.workers` (int), clamp to `>= 1`.
   - Update `load_runtime_config` to include `analysis=_load_analysis_settings(raw)`.

4. `src/sciona/runtime/config/io.py`  
   - Update `write_default_config` template to include:
     ```yaml
     analysis:
       parsing:
         workers: 1
     ```
   - This keeps single-threaded behavior by default.

5. `src/sciona/runtime/config/loaders.py`  
   - Export `analysis` through `load_sciona_config` / `load_runtime_config` (already used by `RepoState`).

6. `src/sciona/pipelines/domain/policies.py`  
   - Extend `AnalysisPolicy` with `parsing_workers: int`.

7. `src/sciona/pipelines/policy/build.py`  
   - Populate `AnalysisPolicy` with `runtime_cfg.analysis.parsing_workers`.

8. `src/sciona/pipelines/exec/build.py`  
   - Pass `parsing_workers` into `BuildEngine(..., parsing_workers=...)`.

9. `src/sciona/code_analysis/core/engine.py`  
   - Add `parsing_workers: int = 1` to `BuildEngine.__init__`.
   - Introduce a small internal dataclass (or tuple) to capture parse outcomes:
     - `index`, `file_snapshot`, `module_name`, `analysis` or `error`.
   - Implement `_analyze_in_threads(...)` using `ThreadPoolExecutor`:
     - Each worker creates its own analyzer instance (`registry.get_analyzer(language)`).
     - No shared parser instance across threads.
     - Collect results into a list indexed by original snapshot order.
   - Persist results in **original deterministic order**:
     - If `error`: increment `parse_failures`, call `_warn`, register module node w/ partial parse metadata (same as today).
     - If `analysis`: `assembler.persist_analysis(...)`.
   - Progress updates happen in deterministic order, after persistence.

10. Tests  
    - Update `tests/test_engine_semantics.py` (or new test file) to run `BuildEngine` with `parsing_workers=2` and confirm:
      - Failed parse still emits module node (existing behavior preserved).
      - Same node/edge counts as single-thread mode for a small fixture.
    - Optional: add a determinism test that compares `compute_structural_hash` between single/multi runs for the same repo fixture.

No new files are strictly required.

---

**Key Design Choices to Preserve Determinism & Avoid DB Races**

**1. DB writes remain single-threaded**
- Only parsing/AST analysis occurs in threads.
- `StructuralAssembler.persist_analysis()` runs on the main thread, in deterministic file order.
- This avoids CoreDB write races and ensures consistent `structural_id` cache use.

**2. Deterministic ordering preserved**
- File discovery is already sorted by `tracked_paths` and preserved through `prepare_file_snapshots`.
- We preserve that order when applying parse results, even if thread completion order differs.
- `progress.advance()` and `_warn()` are invoked in deterministic order to avoid non-repeatable warning sequences.

**3. Analyzer instances are not shared across threads**
- Tree-sitter `Parser` instances are not thread-safe; each worker creates its own analyzer.
- This avoids undefined behavior and race conditions.

**4. Stable structural identifiers and hashes**
- Structural IDs are still derived from node content (`structural_id` function).
- Snapshot hash uses ordered query (`ORDER BY` in `structural_hash_*`), so insertion order is irrelevant as long as content is identical.

---

**Potential Issues & Mitigations**

- **Non-deterministic warning ordering** if warnings are emitted as threads finish.  
  Mitigation: store warnings per file index and emit in original file order.

- **Analyzer thread safety** (tree-sitter `Parser` state).  
  Mitigation: create a fresh analyzer per task; do not share analyzer instances.

- **CoreDB write race** if `StructuralAssembler` used in threads.  
  Mitigation: only parse in threads; all DB writes stay on main thread.

- **GIL limits CPU speedup**.  
  Mitigation: acceptable; tree-sitter is C-backed and may release the GIL for parsing. Even if not, concurrency still benefits IO-bound reads and keeps architecture clean.

- **Resource pressure** if many files load simultaneously.  
  Mitigation: workers limit; `parsing_workers` is bounded and user-controlled.

---

**Config Example**

```yaml
analysis:
  parsing:
    workers: 4
```

Setting `workers: 1` or omitting the block keeps current single-thread behavior.

---

If you want, I can turn this plan into actual code edits. Suggested next steps:
1. Implement config + policy wiring.
2. Implement `BuildEngine` parallel parsing.
3. Add determinism test(s).