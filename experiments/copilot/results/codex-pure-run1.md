## Model

- GPT-5.2-Codex Copilot / VS Code

## Prompt

You are implementing multi-threaded parsing for SCIONA code_analysis layer. Current single thread execution must stay and remain the default. Introduce an optional multi-threaded parsing mode behind an option switch.

The solution must respect the architectural principles described in docs/DEVELOPERGUIDE.md, including SCI immutability, deterministic reducer outputs, stable structural identifiers, and ordering guarantees.

Requirements: parsing results (SCI / reducers) must remain deterministic; no changes in DS schemas; no changes to reducer contracts; no snapshot hash instability; no race conditions in CoreDB / ArtifactDB writes.

Analyse the codebase and propose a detailed implementation plan and concrete code-level modifications. Include a file-by-file list of proposed changes and any new files. Explicitly list potential issues and how you will avoid nondeterminism and DB races.

## Results

- worked for 2m 37s
- explored 28 files, 9 searches, 2 lists

Below is a concrete, deterministic plan for adding **optional multi‑threaded parsing** while keeping single‑thread as the default and preserving all CoreDB/ArtifactDB invariants, schemas, and reducer contracts.

**Plan (high level)**  
1. Add parsing concurrency settings to `.sciona/config.yaml` (default single‑thread).  
2. Thread the new settings through runtime config → build policy → `BuildEngine`.  
3. In `BuildEngine`, keep **all DB writes and ordering in the main thread**. Parallelize **parse-only** work with per‑thread analyzers.  
4. Ensure deterministic ordering by consuming parallel results in the **same sorted file order** as today.  
5. Add tests to prove structural hash is identical for single vs threaded runs and that error/warning behavior stays deterministic.

**Design Details (determinism + safety)**  
- **Single writer**: DB writes remain in the main thread only. No CoreDB/ArtifactDB connection is touched by worker threads.  
- **Per-thread analyzers**: Create analyzers per thread (thread‑local cache) to avoid sharing `tree_sitter.Parser` instances.  
- **Stable ordering**:  
  - `walker.collect_files` already sorts tracked paths.  
  - `changed_snapshots` will be processed in the same order in the main thread.  
  - Worker results are retrieved in deterministic order (iterate futures in index order).  
- **Warnings and parse_failures**: accumulate in the main thread in the same order as today.  
- **No schema changes** and **no reducer contract changes**: only code‑analysis execution strategy changes.

---

## File‑by‑File Proposed Changes

### 1. `src/sciona/runtime/config/models.py`
**Add** new config dataclasses for parsing concurrency (example structure):
- `@dataclass(frozen=True) class ParsingSettings: mode: str; workers: int`
- `@dataclass(frozen=True) class AnalysisSettings: parsing: ParsingSettings`
- Extend `RuntimeConfig` to include `analysis: AnalysisSettings`

### 2. `src/sciona/runtime/config/defaults.py`
**Add** defaults for parsing:
- `DEFAULT_PARSING_MODE = "single"`
- `DEFAULT_PARSING_WORKERS = 0`  (0 means “auto” or “no override”)

### 3. `src/sciona/runtime/config/parse.py`
**Parse** new config block safely:
- `analysis.parsing.mode` (string; allowed: `single`, `threaded`)  
- `analysis.parsing.workers` (int; `<=1` = single‑thread)  
- Fallback to defaults if missing/invalid.

### 4. `src/sciona/runtime/config/io.py`
**Update** `write_default_config()` to include a new optional block:
```yaml
analysis:
  parsing:
    mode: "single"
    workers: 0
```
This preserves backward compatibility and keeps default behavior unchanged.

### 5. `src/sciona/pipelines/domain/policies.py`
**Extend** `AnalysisPolicy` to carry parsing settings:
- `analysis: AnalysisPolicy(languages=..., parsing=...)`

### 6. `src/sciona/pipelines/policy/build.py`
**Populate** `AnalysisPolicy.parsing` from `runtime_cfg.analysis.parsing`.

### 7. `src/sciona/code_analysis/core/engine.py`
**Core change**: add optional multithreaded parsing.  
Proposed additions:
- New constructor param: `parsing_settings: Optional[ParsingSettings] = None`
- Helper to compute worker count and whether to enable threading.

**Implementation shape**:
- Keep `_register_modules()` exactly as is (main thread).
- Replace the analysis loop with:
  - `if threaded:` submit parsing tasks to `ThreadPoolExecutor`  
  - Each task uses **thread‑local** analyzer map keyed by language.  
  - **No DB writes** in tasks.
  - Main thread iterates futures in `changed_snapshots` order, then:
    - On exception → same warning + `parse_failures` handling and `register_module_node` as before.
    - On success → `assembler.persist_analysis(...)` (main thread).
- Keep progress updates and warnings strictly in main thread order.

**Thread‑local analyzer sketch**:
- `thread_local = threading.local()`  
- `thread_local.analyzers = {lang: registry.get_analyzer(lang)}` once per thread  
- Use `file_snapshot.record.language` to select analyzer.

### 8. `src/sciona/code_analysis/core/routing.py` (optional)
If needed for clarity, add a helper to get analyzer factories or avoid using shared analyzer map for threaded path. Not strictly required if thread‑local logic stays in `BuildEngine`.

### 9. Tests
Add/extend tests to ensure determinism and behavior are unchanged:
- `tests/test_snapshot_determinism.py`
  - Build once with single‑threaded parsing.
  - Build once with threaded parsing.
  - Assert identical structural hash and snapshot id.
- `tests/test_engine_semantics.py`
  - Ensure parse failures still create module nodes with the same behavior under threaded mode.

---

## Potential Issues + How We Avoid Them

1. **Non‑deterministic node/edge ordering**
   - Mitigation: DB reads for hash are ordered (`ORDER BY structural_id` / edge ordering).  
   - Main thread inserts in deterministic file order for warnings/progress parity.

2. **Tree‑sitter parser not thread‑safe**
   - Mitigation: No analyzer instance is shared across threads. Each worker has its own analyzer(s) and parser(s).

3. **SQLite thread‑safety / DB races**
   - Mitigation: All DB writes remain in the main thread. Workers only parse and return results.

4. **Snapshot hash instability**
   - Mitigation: Structural hash depends only on DB content; DB content is derived deterministically and written sequentially. Parallel parsing doesn’t alter the content set.

5. **Reducer contract or schema changes**
   - Mitigation: No schema changes and no reducer changes. Only parsing execution mode varies.

---

## Concrete Next Steps

If you want me to proceed to implementation, I’ll:
1. Extend runtime config models + parsers + default config template.  
2. Add the threaded parsing path in `BuildEngine` with deterministic ordering.  
3. Add tests for hash determinism and error behavior.  

If you want a specific config shape or CLI flag instead of config file support, tell me your preference and I’ll align the plan.