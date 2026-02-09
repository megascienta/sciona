# SCIONA Core Developer Guide

Audience: SCIONA core maintainers. This document assumes you already understand
what SCIONA does and why. Architectural invariants are defined in
`ARCHITECTURE.md` and are authoritative.

## Architecture mapped to code

Use `ARCHITECTURE.md` as the normative layer diagram, then map layers to code:

- `runtime/`: paths, config parsing, logging, git plumbing, error surfaces.
- `data_storage/`: CoreDB and ArtifactDB schemas and read/write helpers.
- `code_analysis/`: discovery, parsing, node/edge extraction, normalization.
- `pipelines/`: policy validation, orchestration, build lifecycle, reducer
  execution context, and DB handle ownership.
- `reducers/`: deterministic payload formatting over SCI/Artifact data.
- `api/`: stable public API surface (`sciona.api.*`).

Ownership rule: layers must not reach “up” the stack. For example, reducers must
not own DB connections or discovery, and storage must not enforce policy.

## Where invariants are enforced

`ARCHITECTURE.md` defines the invariants. Enforcement points should be:

- `pipelines/policy`: repo/config validation and clean-worktree enforcement.
- `pipelines/exec`: snapshot lifecycle, artifact rebuild, reducer execution.
- `data_storage/`: schema boundaries and read/write separation.
- `reducers/`: deterministic output formatting over supplied read handles.
- `runtime/`: path safety, git plumbing, and consistent error typing.

If you change invariants, update `ARCHITECTURE.md` first, then adjust these
surfaces to match.

## Changing core safely

Adding a reducer:
- Implement under `reducers/` in the appropriate semantic folder.
- Register it in the reducer registry used by pipelines.
- Add deterministic output tests and update `REDUCERS.md`.
- Validate that it only reads from provided read handles.

Changing pipelines:
- Keep snapshot lifecycle semantics intact.
- Do not expose uncommitted snapshots through public surfaces.
- Ensure artifact rebuilds remain scoped to the latest committed snapshot.
- Update policy checks if the change affects build prerequisites.

Evolving storage/schema:
- Keep CoreDB and ArtifactDB responsibilities separate.
- Prefer additive changes; avoid breaking existing reducers.
- Update read/write helpers and add regression tests.

## Test philosophy

Tests should guard invariants and boundaries rather than surface syntax:

- Boundary tests ensure public API surfaces only depend on `sciona.api.*`.
- Pipeline tests enforce snapshot lifecycle and artifact rebuild behavior.
- Reducer tests validate deterministic, ordered payloads.
- Storage tests validate schema invariants and read/write separation.

## Documentation discipline

- `ARCHITECTURE.md` is the single source of truth for invariants.
- Other documents may reference but must not restate those invariants.
