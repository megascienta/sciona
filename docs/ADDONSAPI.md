# SCIONA Addons API Reference

This document lists the stable addon-facing API exported by `sciona.api.addons`. All access is read-only. Core does not load, discover, or register addons.

## Exports

- `PLUGIN_API_VERSION` (str): current plugin API version, e.g. `"1.0"`.
- `PLUGIN_API_MAJOR` (int): major plugin API version.
- `PLUGIN_API_MINOR` (int): minor plugin API version.
- `emit` (callable): render reducer output (read-only).
- `list_entries` (callable): list available reducers (read-only).
- `open_core_readonly` (callable): open CoreDB connection (read-only).
- `open_artifact_readonly` (callable): open ArtifactDB connection (read-only).
- `core_readonly` (context manager): CoreDB connection scope (read-only).
- `artifact_readonly` (context manager): ArtifactDB connection scope (read-only).

## Reducer helpers

Function: `list_entries(repo_root: Path | None = None, *, include_hidden: bool = False) -> list[dict[str, object]]`

Returns reducer metadata entries sorted by `reducer_id`.

Function: `emit(reducer_id: str, *, repo_root: Path | None = None, diff_mode: str = "full", **kwargs: object) -> tuple[str, str, dict[str, object]]`

Renders a reducer payload for the latest committed snapshot. `diff_mode` must be `"full"` or `"summary"`. Raises a workflow error if no committed snapshot exists.

## Storage helpers (read-only)

Function: `open_core_readonly(repo_root: Path | None = None)`

Returns a read-only CoreDB connection. Caller is responsible for closing it.

Function: `open_artifact_readonly(repo_root: Path | None = None)`

Returns a read-only ArtifactDB connection. Caller is responsible for closing it.

Function: `core_readonly(repo_root: Path | None = None)`

Context manager yielding a read-only CoreDB connection.

Function: `artifact_readonly(repo_root: Path | None = None)`

Context manager yielding a read-only ArtifactDB connection.

## Repo root resolution

All helpers accept `repo_root: Path | None`. When `None`, the repo root is resolved from the current working directory.
