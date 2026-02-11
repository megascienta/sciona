# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import json
from typing import Iterable

from sciona import api


def _parse_json_payload(text: str) -> dict:
    stripped = text.strip()
    assert stripped.startswith("```json")
    body = stripped.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(body)


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
    text, _, _ = api.addons.emit(
        "module_overview",
        repo_root=repo_root,
        module_id="pkg.alpha",
    )
    payload = _parse_json_payload(text)
    forbidden = {"snapshot_id", "created_at", "git_commit_time"}
    assert not _find_forbidden_keys(payload, forbidden)
