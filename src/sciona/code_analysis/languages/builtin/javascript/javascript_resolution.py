# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""JavaScript instance/alias resolution wrappers."""

from __future__ import annotations

from ..typescript.typescript_resolution import (
    collect_callable_typed_binding_instance_map,
    resolve_pending_instances,
)

__all__ = [
    "collect_callable_typed_binding_instance_map",
    "resolve_pending_instances",
]

