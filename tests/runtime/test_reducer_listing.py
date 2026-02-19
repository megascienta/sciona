# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.runtime.reducer_listing import (
    format_reducer_call,
    render_reducer_catalog,
    render_reducer_list,
)


class _DummyReducer:
    def render(
        self,
        snapshot_id,
        conn,
        repo_root,
        *,
        module_id,
        limit=5,
        extras=None,
    ) -> str:
        return ""


class _ReducerEntry:
    def __init__(self, module):
        self.module = module


def test_format_reducer_call_includes_flags() -> None:
    call = format_reducer_call("dummy", _DummyReducer())
    assert call.startswith("reducer --id dummy")
    assert "--module-id MODULE_ID" in call
    assert "[--limit LIMIT]" in call
    assert "[--extras]" in call


def test_render_reducer_list_orders_categories() -> None:
    entries = [
        {"reducer_id": "b", "category": "analytics", "summary": "B"},
        {"reducer_id": "a", "category": "core", "summary": "A"},
    ]
    reducers = {
        "a": _ReducerEntry(_DummyReducer()),
        "b": _ReducerEntry(_DummyReducer()),
    }
    lines = render_reducer_list(entries, reducers, include_prefix=False)
    core_index = lines.index("Category: core")
    analytics_index = lines.index("Category: analytics")
    assert core_index < analytics_index
    assert any(line.startswith("  Command: reducer --id a") for line in lines)


def test_render_reducer_catalog_lists_entries() -> None:
    entries = [
        {"reducer_id": "alpha", "category": "core", "summary": "Alpha"},
    ]
    lines = render_reducer_catalog(entries)
    assert "Available reducers:" in lines[0]
    assert "- alpha" in lines
