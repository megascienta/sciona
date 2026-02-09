# SCIONA

SCIONA builds a **deterministic structural index (SCI)** for a Git repository. It records *what exists* in code (modules, classes, functions, methods) and *how entities are structurally connected*.

SCIONA is **snapshot-based, reducer-driven, and LLM-agnostic**. It does not execute code, infer intent, or perform semantic retrieval. Reducers are the truth surfaces: they render structural facts deterministically from a **committed snapshot**.

By providing an explicit, deterministic representation of structural truth, SCIONA can be used to **anchor LLM-assisted workflows**: downstream tools may reason only over reducer outputs, rather than reconstructing structure heuristically or hallucinating it from source text.

---

## Why SCIONA exists

When working with large, long-lived codebases, we repeatedly encountered the same failure mode:

LLM assistance starts out helpful, but gradually becomes inconsistent. Earlier assumptions are contradicted. Structural constraints are forgotten. The model continues to “sound right” while no longer reflecting the actual code.

This is not primarily an LLM problem. It is a **context problem**.

In real-world software systems, the relevant information is not just which functions exist, but how files, modules, symbols, and dependencies are *structurally connected* and can be reasoned about consistently.

Most LLM tooling today relies on embeddings, semantic retrieval, or opaque context assembly. These approaches are powerful, but difficult to make reproducible and hard to constrain over long sessions, refactors, or collaboration boundaries.

SCIONA takes a deliberately different approach.

It builds a **deterministic structural snapshot** of a codebase: no embeddings, no semantic guessing, no code execution. Just an explicit, versioned representation of structural truth that downstream tools, including LLM copilots, can be constrained by, rather than asked to hallucinate around.

SCIONA is opinionated and intentionally limited in scope. It provides structure, not interpretation.

---

## Core guarantees (summary)

Authoritative definitions live in `ARCHITECTURE.md`. At a glance:

- **No code execution**
- **Snapshot-only truth** (latest committed snapshot)
- **Read-only w.r.t. the repo**, except `.sciona/` and explicit setup commands
- **Deterministic outputs** for the same snapshot, config, and version
- **LLM-agnostic** (no provider or prompt assumptions)

---

## How SCIONA can be used today

SCIONA can be used directly via its CLI or integrated into LLM-assisted workflows.

One supported mode of operation is interaction through an LLM copilot guided
by an auto-generated `AGENTS.md` file in the repository root. This file serves
as a control surface for the copilot by explicitly specifying how SCIONA should
be used during code reasoning.

In particular, `AGENTS.md`:
- enforces *SCIONA-first* discipline for structural questions
- specifies which reducers to run before any interpretation
- defines snapshot vs dirty-worktree semantics
- requires explicit declaration when SCIONA cannot be used

In this mode, the copilot is instructed to reason only over reducer outputs, rather than reconstructing structure heuristically from source text.

Manual CLI usage is fully supported and provides a complete interface for non-copilot workflows.

---

## Quick start (minimal)

Default install: `pip install sciona` or `pip install git+https://github.com/megascienta/sciona`
Development install: `pip install -e ".[dev]"`

```bash
cd /path/to/repo
sciona init
$EDITOR .sciona/config.yaml   # enable languages
sciona build
sciona status
````

Explore available reducers:

```bash
sciona reducer list
sciona reducer --id module_overview --module-id pkg.mod
```

For copilot-driven workflows, start with `AGENTS.md` in the repo root.

---

## Discovery and scope (high level)

* Only **git-tracked files** are analyzed
* Only **enabled languages** are indexed
* `.gitignore` is respected for tracked files
* No directory walking
* No runtime import resolution

If the worktree is dirty, reducers may include a best-effort `_diff` overlay. Overlays are **non-authoritative hints**, not structural truth.

---

## If you want X, read Y

* **Understand user expectations and limitations** → `USERGUIDE.md`
* **See binding behavioral rules** → `CONTRACTS.md`
* **Understand architecture and invariants** → `ARCHITECTURE.md`
* **Work on SCIONA core safely** → `COREDEVGUIDE.md`
* **Build addons independently** → `ADDONSDEVGUIDE.md`