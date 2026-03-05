# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""JavaScript call extraction and resolution wrappers."""

from __future__ import annotations

from ..typescript.typescript_calls import callee_text, resolve_typescript_calls


def resolve_javascript_calls(*args, **kwargs):
    return resolve_typescript_calls(*args, **kwargs)


__all__ = ["callee_text", "resolve_javascript_calls"]

