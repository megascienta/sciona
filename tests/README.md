# Tests

This test suite is organized by SCIONA layers to keep responsibilities clear and avoid overlap.

Layer layout:
- `tests/runtime/`: paths, config, logging, git plumbing, runtime helpers
- `tests/data_storage/`: CoreDB/ArtifactDB schemas, read/write helpers, storage invariants
- `tests/code_analysis/`: discovery, parsing, extraction, normalization, analysis tools
- `tests/analysis_contracts/`: admissibility gates and strict call-resolution contracts
- `tests/pipelines/`: policy validation, snapshot lifecycle, build orchestration, diff overlays
- `tests/reducers/`: reducer outputs, registry metadata, deterministic rendering
- `tests/api/`: public API surface and addon boundaries
- `tests/cli/`: CLI command behavior and CLI support helpers

Scope expectations:
- Tests should target one layer’s responsibilities and avoid reaching upward in the stack.
- Cross-layer behavior should be asserted via the owning layer’s API only.
- Determinism tests must avoid timestamps, randomness, or nondeterministic ordering.

Conventions:
- Prefer `tests/helpers.py` for shared fixtures and seed utilities.
- Keep test modules small and focused; group related cases within a single file.
- Use descriptive `test_*` names that reflect the layer responsibility being validated.
