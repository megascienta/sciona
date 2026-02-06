# SCIONA

**User Guide.**
This document explains how to run SCIONA. It does not define system invariants.

SCIONA is a deterministic CLI tool that builds a structural code index (SCI) for a
Git repository. It records structural facts (nodes + edges) per snapshot and stores
state under `.sciona/` in the target repo.

For system invariants and contracts, see:
- `ARCHITECTURE.md`
- `CONTRACTS.md`
- `REDUCERS.md`

---

## Install

SCIONA requires Python 3.11 and Tree-sitter runtimes.

```bash
pip install -e . --no-build-isolation
```

---

## Quick start

SCIONA operates on the **current repo** and only on **git-tracked files**.

```bash
cd /path/to/repo
sciona init
sciona init --agents
sciona init --agents-append
sciona init --agents-overwrite
# edit .sciona/config.yaml to enable languages
sciona build
sciona status
sciona clean --agents
```

Important rules:
- Build requires a **clean worktree** for tracked language files.
- Read-only commands may proceed on a dirty worktree but warn that outputs reflect
  the last committed snapshot.
- When the worktree is dirty, reducer and prompt payloads may include a best-effort
  `_diff` overlay and patched structural fields to reflect local changes. Overlays
  use the merge-base between the snapshot commit and `HEAD`, and ignore submodules.
- All read operations use the **latest committed snapshot** only.

---

## Configuration

`sciona init` creates `.sciona/config.yaml`. Languages are disabled by default.
Enable at least one language before `build`:

```yaml
languages:
  python:
    enabled: true

# optional
# discovery:
#   exclude_globs:
#     - "**/node_modules/**"
#     - "**/dist/**"
```

Supported languages (1.0): Python, TypeScript, Java.

Discovery rules (authoritative):
- SCIONA asks git for the tracked file list (repo-relative POSIX paths).
- Hard excludes: `.git/**`, `.sciona/**`.
- Applies `discovery.exclude_globs` (gitwildmatch semantics).
- Only enabled-language extensions are eligible.
- `.gitignore` is respected for tracked files that are explicitly ignored.
- No directory walking.

---

## Build and status

```bash
sciona build     # create or reuse latest committed snapshot (clean worktree required)
sciona status    # show latest snapshot and DB state (warns if dirty)
```

Snapshot semantics are defined in `ARCHITECTURE.md` and `CONTRACTS.md`.
SCIONA keeps exactly one committed snapshot after a successful build.
ArtifactDB is refreshed after the core snapshot commit and tracked with internal rebuild status markers.
Read-only commands warn when the worktree is dirty because outputs reflect the
last committed snapshot.

---

## Prompts

SCIONA ships core prompt templates and a registry in `.sciona/prompts`
(seeded during `sciona init`). Users may add their own templates and extend
`registry.yaml` at their own risk, using core reducers and placeholders.
Addon prompts are not exposed through the core CLI.
Bundled prompt ids:
- preflight_v1
- architecture_overview_v1
- risk_radar_v1

```bash
sciona prompt run preflight_v1
sciona prompt run preflight_v1 --answer
```

Use `--json` to emit machine-readable prompt payloads. JSON output includes the
full prompt text plus split `prompt_header`, `prompt_body`, `instructions`,
`evidence`, and `resolved_arg_map` fields for easier parsing.
Prompt output is human-readable by default.

List prompts and inspect their metadata:

```bash
sciona prompt list
sciona prompt info --id preflight_v1
```

`prompt list` shows only the args declared by each prompt registry entry
(required/optional/default). Reducer render options outside those declared args
are not shown or accepted.

LLM settings live in `.sciona/config.yaml`:

```yaml
llm:
  provider: "openai"
  model: "gpt-4.1"
  api_key: null
  api_endpoint: null
  temperature: 0.0
```

Prompt templates and the registry live in `.sciona/prompts`.
See `REDUCERS.md` for the full list of reducers and placeholders, and use
`sciona reducer list` + `sciona reducer info --id <reducer_id>` for reducer args.

---

## Code assembly

Assemble deterministic code payloads using the baseline reducer:

```bash
sciona reducer --id concatenated_source --scope codebase
sciona reducer --id concatenated_source --scope module --module-id=<id>
sciona reducer --id concatenated_source --scope class --class-id=<id>
```

---

## Resolve identifiers

Use the resolver to map qualified names to structural ids.

```bash
sciona resolve pkg.alpha.service.helper --kind callable --limit 10
sciona resolve pkg.alpha --kind module --limit 10
sciona resolve pkg.alpha --kind module --limit 10 --json
```

If there is no exact match, SCIONA prints best-fit candidates and suggests using `--id`
for disambiguation.

---

## Search symbols

```bash
sciona search pkg.alpha --kind module --limit 10
sciona search pkg.alpha --kind module --limit 10 --json
sciona search pkg.alpha --kind any --limit 10
```

---

## Import references

```bash
sciona refs pkg.alpha
sciona refs pkg.alpha --json
sciona refs pkg.alpha --edge-type IMPORTS_DECLARED --limit 25
```

---

## Reducer examples

```bash
sciona search pkg.alpha --kind module --limit 10
sciona reducer --id dependency_edges --module-id pkg.alpha
sciona reducer --id import_references --module-id pkg.alpha
sciona reducer --id importers_index --module-id pkg.alpha
sciona reducer --id symbol_references --query pkg.alpha --kind module --limit 10
sciona reducer --id file_outline --module-id pkg.alpha
sciona reducer --id module_file_map --module-id pkg.alpha
sciona reducer --id callsite_index --callable-id pkg.alpha.service.helper --direction both
sciona reducer --id callable_source --callable-id pkg.alpha.service.helper
```
Reducers emit machine-readable JSON by default; use `--json` on prompts for the same.

---

## Files under .sciona/

- `sciona.db` — structural index (SCI)
- `sciona.artifacts.db` — derived artifacts (see `ARCHITECTURE.md`)
- `sciona.log` — logs (if logging is enabled and repo is initialized)

If you see schema mismatch errors in 1.0, remove `.sciona/` and re-init.
