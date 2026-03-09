# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import pytest

from sciona.reducers.helpers.render import render_json_payload, require_connection


def test_require_connection_raises_for_none() -> None:
    with pytest.raises(ValueError, match="open database connection"):
        require_connection(None)


def test_require_connection_returns_same_connection() -> None:
    sentinel = object()
    assert require_connection(sentinel) is sentinel

def test_render_json_payload_returns_structured_payload() -> None:
    rendered = render_json_payload({"b": 2, "a": {"d": 4, "c": 3}})
    assert rendered == {"b": 2, "a": {"d": 4, "c": 3}}
