# SCIONA Addons Guide

This document is self-contained for addon developers. It is intended to live
in addons repositories. Addons consume core as a library via `sciona.api.*`
and must treat storage as read-only.
For user-facing expectations and the public contract, see `USERGUIDE.md` in
the core repo.

## What addons can do

Addons can register additional CLI commands under their own namespace.
Addons must not register reducers (core-owned for determinism and DB lifecycle
ownership). Prefer reducer emission as the primary contract for reading data.

## Entry point

Addons are separate products that consume core as a library. Core does not
discover or load addons. If your addon product uses an entry-point loader,
it may define a `sciona.addons` group and a callable that accepts a `Registry`.

## Registry API

The addon registry supports:
- `register_cli(name, app)` to register a Typer-compatible CLI app.

Reducers are core-owned and cannot be registered by addons.

## Compatibility contract

Addons declare the plugin API version via:
- `REQUIRES_SCIONA_PLUGIN_API` (module or function attribute)

Supported formats:
- integer major (e.g., `1`)
- string major or major.minor (e.g., `"1"`, `"1.0"`)
- range string (e.g., `">=1,<2"`)

Versioning policy:
- Major bump: breaking changes to Registry API.
- Minor bump: additive, backward-compatible changes.

Compatibility checks are enforced by the addon product.

## Disable addons

Not applicable in core. Addon loading (if any) is owned by external products.

## Hello addon (minimal walkthrough)

1. Install your addon package into the environment.
2. Run `sciona --help` and confirm your namespace appears.
3. Run your addon command via `sciona <your-namespace> ...`.

## Packaging and testing

- Package as a standard Python project with entry points.
- Test CLI integration by invoking `sciona` with your addon installed.

## Limitations

- Addons do not modify SCIONA core snapshots or reducers.
- Addons should not rely on private/internal APIs.
- Addons may open CoreDB/ArtifactDB in **read-only** mode via `sciona.api.storage`
  or `sciona.api.addons` helpers.

For core behavior, see `README.md` and `USERGUIDE.md` in the core repo.
