# SCIONA Addons Guide

This guide defines the supported addon-facing surface for SCIONA.

For addon code, `sciona.api.addons` is the stable public entrypoint. Core,
pipeline, reducer, and storage internals are not addon APIs unless they are
re-exported there.

If this guide conflicts with `docs/CONTRACT.md`, the contract wins.

## Scope

Use this document for:

- addon-facing imports and compatibility boundaries;
- stable public exports for addon code;
- read-only data access expectations;
- reducer integration from addon code;
- addon-specific testing expectations.

Do not use this document to infer stability for internal modules.

## Public API

Stable public addon surface: `sciona.api.addons`

Public exports:

- `PLUGIN_API_VERSION`, `PLUGIN_API_MAJOR`, `PLUGIN_API_MINOR`
- `list_entries(...)`
- `get_entry(...)`
- `emit(...)`
- `open_core_readonly(...)`, `open_artifact_readonly(...)`
- `core_readonly(...)`, `artifact_readonly(...)`

The root public namespace remains `sciona.api`, which exposes only `addons`.

## Import Rules

- Addon code should import SCIONA through `sciona.api.addons`
- Direct imports from internal modules such as `sciona.pipelines.*`,
  `sciona.data_storage.*`, `sciona.reducers.*`, and
  `sciona.code_analysis.*` are unsupported for addon code
- If a repo-level `addons/` tree exists, its modules are treated as
  `sciona.addons.*` for import-boundary validation

## Compatibility Contract

- Addon compatibility is versioned through
  `PLUGIN_API_MAJOR`, `PLUGIN_API_MINOR`, and `PLUGIN_API_VERSION`
- Major-version compatibility is the boundary that addon code should treat as
  required
- New addon-facing helpers must be exposed through `sciona.api.addons` before
  they are considered public

## Data Access Model

- Addon-facing database helpers are read-only wrappers around connection
  helpers and repo-root resolution
- CoreDB is the committed structural source of truth for structural identities
  and metadata
- ArtifactDB is the reducer-facing derived store for call projections, rollups,
  diagnostics, and overlay-backed reducer surfaces
- Addons must not assume write access to either database through the public API

## Reducer Integration

- Use `list_entries(...)` and `get_entry(...)` to discover reducer metadata
- Use `emit(...)` to request reducer payloads
- Reducer payloads are defined against the committed snapshot
- Dirty-worktree overlay behavior depends on reducer support; overlay metadata
  is advisory rather than committed structural truth

## Addon Layout

If a repository contains addon code, keep it in a repo-level `addons/` tree.

This layout is a repository convention used by import-boundary validation. It
does not make addon internals part of the SCIONA public API.
