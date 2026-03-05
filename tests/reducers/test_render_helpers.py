# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import json

import pytest

from sciona.reducers.helpers.render import render_json_payload, require_connection


def test_require_connection_raises_for_none() -> None:
    with pytest.raises(ValueError, match="open database connection"):
        require_connection(None)


def test_require_connection_returns_same_connection() -> None:
    sentinel = object()
    assert require_connection(sentinel) is sentinel


def test_render_json_payload_wraps_and_sorts() -> None:
    rendered = render_json_payload({"b": 2, "a": {"d": 4, "c": 3}})
    assert rendered.startswith("```json\n")
    assert rendered.endswith("\n```")
    body = rendered.removeprefix("```json\n").removesuffix("\n```")
    assert body == json.dumps({"a": {"c": 3, "d": 4}, "b": 2}, sort_keys=True)
