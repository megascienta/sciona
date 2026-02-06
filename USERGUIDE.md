# SCIONA User Guide (Expectations + Limitations)

This document explains what SCIONA does under the hood and what to expect from
its outputs. It is written for users, not developers.

## What SCIONA is

SCIONA builds a deterministic structural code index (SCI) from a Git repository.
It extracts structural facts (nodes + edges) and stores them as a committed
snapshot. All read operations are anchored to the latest committed snapshot.

## What SCIONA is not

- It is not a runtime analyzer.
- It does not execute code or import modules.
- It does not resolve dynamic dispatch or runtime reflection.

## Snapshot model

- A snapshot is a committed, immutable view of tracked source files.
- SCIONA keeps a single latest committed snapshot after each successful build.
- Read-only commands always target the latest committed snapshot.

## Clean vs dirty worktree

- Build requires a clean worktree for tracked language files in scope.
- Untracked files do not block builds.
- If the worktree is dirty, read-only commands warn that outputs reflect the
  last committed snapshot.

### Dirty-worktree overlays (`_diff`)

When the worktree is dirty, reducer and prompt payloads may include a best-effort
`_diff` overlay. This overlay is non-authoritative and exists to help you reason
about local changes without rebuilding.

`_diff` provides:
- baseline metadata (snapshot/head/merge-base)
- patch coverage and warnings
- node/edge/call deltas and summary stats

If `_diff` is present, treat it as the primary evidence for dirty changes. If
`_diff` is missing and you need accuracy, commit and run `sciona build`.

## Discovery scope

- Only git-tracked files are analyzed.
- `.gitignore` is respected for tracked files explicitly ignored.
- No directory walking is performed.
- Language support is based on file extensions for enabled languages.

## Structural accuracy limits

SCIONA captures structure, not full semantics.

- Imports are syntax-based hints, not full resolution.
- Call graphs are derived artifacts and may be incomplete.
- Module names are derived from repo-relative paths only.

## Determinism

Given the same repository snapshot, SCIONA outputs are deterministic and stable.

## Security model

- SCIONA analysis does not execute code.
- No network calls are used during analysis or reducers.

## Practical expectations

You should expect:
- Stable structure for committed code.
- Best-effort, non-authoritative hints for dirty changes.
- Clear warnings when your working tree is dirty or unsupported.

If you need authoritative results, commit and rebuild.
