# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from typing import Iterable

from sciona.pipelines.ops.reducers import emit
from tests.helpers import parse_json_payload, qualify_repo_name


def _find_forbidden_keys(payload: object, forbidden: Iterable[str]) -> set[str]:
    forbidden_set = set(forbidden)
    found: set[str] = set()
    stack = [payload]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                if key in forbidden_set:
                    found.add(key)
                stack.append(value)
        elif isinstance(current, list):
            stack.extend(current)
    return found


def test_reducer_payload_excludes_snapshot_metadata(repo_with_snapshot):
    repo_root, _snapshot_id = repo_with_snapshot
    payload, _, _ = emit(
        "module_overview",
        repo_root=repo_root,
        module_id=qualify_repo_name(repo_root, "pkg.alpha"),
    )
    payload = parse_json_payload(payload)
    forbidden = {"snapshot_id", "created_at", "git_commit_time"}
    assert not _find_forbidden_keys(payload, forbidden)
