# SCIONA Addons Developer Guide

This document is fully standalone for addon authors. You do not need core
internal docs to build a compatible addon.

## What addons are

Addons are separate products that extend SCIONA through the public API. Core
never discovers or loads addons; any loading mechanism is owned by your addon
product or packaging system.

## What addons are allowed to do

- Register additional CLI commands under their own namespace.
- Consume reducer outputs as the primary contract for reading data.
- Open CoreDB/ArtifactDB in **read-only** mode via `sciona.api.storage` or
  `sciona.api.addons` helpers.

## What addons must never do

- Register reducers or prompts into core.
- Mutate snapshots or artifacts.
- Rely on internal modules or storage schemas.

## Public API surface

Your addon must use `sciona.api.*` only. The relevant surfaces are:

- `sciona.api.addons` for addon integration helpers
- `sciona.api.reducers` for reducer registry and rendering helpers
- `sciona.api.storage` for **read-only** CoreDB/ArtifactDB access
- `sciona.api.errors` for public error types

Anything outside `sciona.api.*` is internal and may change without notice.

## Entry point and registry

If your addon product uses entry points, define a `sciona.addons` group and a
callable that accepts a `Registry`.

The addon registry supports:
- `register_cli(name, app)` to register a Typer-compatible CLI app.

Reducers are core-owned and cannot be registered by addons.

## Compatibility model

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

## Packaging and testing

- Package as a standard Python project with entry points.
- Test CLI integration by invoking `sciona` with your addon installed.
- Validate that all storage access is read-only.

## Limitations (by design)

- Addons do not modify SCIONA core snapshots or reducers.
- Addons should treat reducer outputs as the primary truth surface.
- Addons must assume internal modules can change at any time.
