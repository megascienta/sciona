# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Artifact DB connection helpers."""

from __future__ import annotations


def connect(db_path, *, repo_root=None):
    from ..connections import connect_artifact

    return connect_artifact(db_path, repo_root=repo_root)


__all__ = ["connect"]
