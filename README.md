# SCIONA

## Intro

SCIONA builds a deterministic structural code index (SCI) for a Git repository.
It records structural facts (nodes + edges) per snapshot and stores state under
`.sciona/` in the target repo. The goal is to anchor reasoning to structural
truth and keep analysis reproducible.

## Docs (Audience + Purpose)

- `README.md` — simple user guide (install, run, common commands).
- `USERGUIDE.md` — expectations + limitations (what SCIONA does under the hood).
- `DEVELOPER.md` — developer guide (architecture, extending, tests).
- `ADDONS.md` — addons developer guide (self-contained for addons repos).

---

## Install

SCIONA requires Python 3.11 and Tree-sitter runtimes.

```bash
pip install -e . --no-build-isolation
```

---

## Quick start

SCIONA operates on the current repo and only on git-tracked files.

```bash
cd /path/to/repo
sciona init
# edit .sciona/config.yaml to enable languages
sciona build
sciona status
```

Key rules:
- Build requires a clean worktree for tracked language files in scope.
- Untracked files do not block builds.
- Read-only commands may proceed on a dirty worktree but warn that outputs reflect
  the latest committed snapshot.
- Dirty worktrees may include a best-effort `_diff` overlay in reducer/prompt payloads.

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

Discovery rules:
- SCIONA asks git for tracked file paths (repo-relative POSIX paths).
- Hard excludes: `.git/**`, `.sciona/**`.
- Applies `discovery.exclude_globs` (gitwildmatch semantics).
- Only enabled-language extensions are eligible.
- `.gitignore` is respected for tracked files explicitly ignored.
- No directory walking.

---

## Common commands

Build + status:
```bash
sciona build
sciona status
```

Prompts:
```bash
sciona prompt list
sciona prompt run preflight_v1
sciona prompt run preflight_v1 --answer
```

Reducers:
```bash
sciona reducer list
sciona reducer info --id module_overview
```

Resolve and search:
```bash
sciona resolve pkg.alpha --kind module --limit 10
sciona search pkg.alpha --kind module --limit 10
```

Clean:
```bash
sciona clean
```
Notes:
- `sciona clean` cancels if custom prompts are registered in `.sciona/prompts/registry.yaml`.
  Remove or reset custom entries first.

Hooks (optional):
```bash
sciona hooks install
sciona hooks status
sciona hooks remove
```

`sciona init` also supports:
```bash
sciona init --post-commit-hook
sciona init --post-commit-hook-command "sciona build"
```

---

## Prompt configuration

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
Use `DEVELOPER.md` for implementation details.
