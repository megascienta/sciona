# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Core DB connection helpers."""

from __future__ import annotations


def connect(db_path, *, repo_root=None):
    from ..connections import connect_core

    return connect_core(db_path, repo_root=repo_root)


__all__ = ["connect"]
