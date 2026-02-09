# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import sqlite3

import pytest

from sciona import api


def test_open_core_readonly_rejects_writes(repo_with_snapshot, monkeypatch):
    repo_root, _snapshot_id = repo_with_snapshot
    with api.storage.core_readonly(repo_root) as conn:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("CREATE TABLE readonly_test(x INTEGER)")


def test_open_artifact_readonly_rejects_writes(repo_with_snapshot, monkeypatch):
    repo_root, _snapshot_id = repo_with_snapshot
    with api.storage.artifact_readonly(repo_root) as conn:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("CREATE TABLE readonly_test(x INTEGER)")
