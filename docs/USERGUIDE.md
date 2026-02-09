# SCIONA User Guide

This document explains how to use SCIONA. It describes the mental model, what results can be trusted, and how SCIONA can be used together with an LLM copilot.

For architectural invariants and data-flow rules, defer to `ARCHITECTURE.md`.

---

## Mental model

- **Snapshot**: the latest committed snapshot of tracked source files.
- **Reducers**: read-only truth surfaces over the snapshot.
- **Dirty overlay**: a best-effort `_diff` overlay for uncommitted changes.

---

## What you can trust

**Authoritative:**
- Reducer payloads derived from the latest committed snapshot.
- Stable structural relationships for committed code.

**Best-effort:**
- `_diff` overlays representing uncommitted changes.
- Warnings and coverage metadata when overlays are incomplete or unavailable.

**When in doubt:**
- Commit changes and run `sciona build` to refresh the snapshot.
- If `_diff` is missing and accuracy matters, rebuild before reasoning.

---

## Using SCIONA with a copilot (recommended)

`AGENTS.md` acts as the control plane for copilot-assisted workflows. It defines:
- SCIONA-first discipline (reducers before interpretation).
- Evidence-before-interpretation rules.
- Snapshot and dirty-worktree semantics.

When using a copilot, read the repository’s `AGENTS.md` and follow it exactly.

---

## Reducer catalog (by intention)

This catalog groups reducers by intent. Availability depends on configuration and SCIONA version.

**Orientation (what exists, where it lives):**
- `structural_index`
- `module_overview`
- `class_overview`
- `callable_overview`

**Local structure and source context:**
- `file_outline`
- `module_file_map`
- `callable_source`
- `concatenated_source`

**Impact and relationships (calls, imports, usage):**
- `call_graph`
- `callsite_index`
- `class_call_graph`
- `module_call_graph`
- `importers_index`
- `dependency_edges`
- `import_references`
- `symbol_lookup`
- `symbol_references`
- `fan_summary`
- `hotspot_summary`

---

## Limitations

- SCIONA captures structure, not semantics.
- SCIONA does not execute code or resolve runtime behavior.
- Symbol resolution is syntax-driven and best-effort.

---

## Discovery scope

- Only git-tracked files are analyzed.
- `.gitignore` applies to files that are explicitly ignored.
- Discovery is extension-based for enabled languages.