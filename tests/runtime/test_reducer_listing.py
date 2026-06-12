# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.runtime.reducers.listing import (
    format_reducer_call,
    normalize_category,
    render_reducer_catalog,
    render_reducer_list,
)
from sciona.cli.support.render import render_reducer_show


class _DummyReducer:
    def render(
        self,
        snapshot_id,
        conn,
        repo_root,
        *,
        module_id,
        compact: bool | None = None,
        top_k: int | None = None,
        limit=5,
        extras=None,
    ) -> str:
        return ""


class _ReducerEntry:
    def __init__(self, module, category="orientation"):
        self.module = module
        self.category = category


def test_format_reducer_call_includes_flags() -> None:
    call = format_reducer_call("dummy", _DummyReducer())
    assert call.startswith("reducer --id dummy")
    assert "--module-id MODULE_ID" in call
    assert "[--compact]" in call
    assert "[--top-k TOP_K]" in call
    assert "[--limit LIMIT]" in call
    assert "[--extras]" in call


class _OptionalArgsReducer:
    def render(
        self,
        snapshot_id,
        conn,
        repo_root,
        callable_id=None,
        top_k=None,
    ) -> str:
        return ""


def test_format_reducer_call_honors_required_metadata() -> None:
    args = [
        {"name": "callable_id", "required": True},
        {"name": "top_k", "required": False},
    ]
    call = format_reducer_call("dummy", _OptionalArgsReducer(), args)
    assert "--callable-id CALLABLE_ID" in call
    assert "[--callable-id" not in call
    assert "[--top-k TOP_K]" in call


def test_render_reducer_list_orders_roles() -> None:
    entries = [
        {"reducer_id": "b", "category": "source", "summary": "B"},
        {"reducer_id": "a", "category": "orientation", "summary": "A"},
    ]
    reducers = {
        "a": _ReducerEntry(_DummyReducer(), "orientation"),
        "b": _ReducerEntry(_DummyReducer(), "source"),
    }
    lines = render_reducer_list(entries, reducers, include_prefix=False)
    orientation_index = lines.index("Category: orientation")
    source_index = lines.index("Category: source")
    assert orientation_index < source_index
    assert any(line.startswith("  Command: reducer --id a") for line in lines)
    assert "  Compact: yes (`--compact` [`--top-k` TOP_K] [`--limit` LIMIT])" in lines
    assert "  Summary: A" in lines


def test_render_reducer_catalog_lists_entries() -> None:
    entries = [
        {
            "reducer_id": "alpha",
            "category": "orientation",
            "summary": "Alpha",
        },
    ]
    lines = render_reducer_catalog(entries)
    assert "Available reducers:" in lines[0]
    assert "- alpha" in lines
    assert "  Summary: Alpha" in lines


def test_normalize_category_defaults_to_unknown() -> None:
    assert normalize_category("") == "unknown"
    assert normalize_category(" source ") == "source"


def test_render_reducer_show_excludes_removed_metadata() -> None:
    lines = render_reducer_show(
        {
            "reducer_id": "alpha",
            "category": "source",
            "placeholder": "ALPHA",
            "summary": "Alpha.",
        }
    )
    assert "Category: source" in lines
    assert not any(line.startswith("Risk tier:") for line in lines)
    assert not any(line.startswith("Stage:") for line in lines)
    assert "Placeholder: ALPHA" in lines
    assert "Arguments:" in lines
    assert "  none" in lines


def test_render_reducer_show_renders_argument_documentation() -> None:
    lines = render_reducer_show(
        {
            "reducer_id": "alpha",
            "category": "source",
            "placeholder": "ALPHA",
            "summary": "Alpha.",
            "args": [
                {
                    "name": "module_id",
                    "type": "str",
                    "description": "Module filter.",
                    "required": True,
                    "enum": [],
                    "default": None,
                },
                {
                    "name": "direction",
                    "type": "str",
                    "description": "Edge direction.",
                    "required": False,
                    "enum": ["in", "out", "both"],
                    "default": "both",
                },
                {
                    "name": "compact",
                    "type": "bool",
                    "description": "Compact payload.",
                    "required": False,
                    "enum": [],
                    "default": "false",
                },
            ],
            "requires": "one of --module-id / --callable-id",
        }
    )
    assert "  --module-id MODULE_ID (str, required)" in lines
    assert "      Module filter." in lines
    assert "  --direction DIRECTION (str, optional; one of: in, out, both; default: both)" in lines
    assert "  --compact (bool, optional; default: false)" in lines
    assert "Requires: one of --module-id / --callable-id" in lines
