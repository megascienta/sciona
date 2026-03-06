# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.runtime.reducer_listing import (
    format_reducer_call,
    normalize_category,
    render_reducer_catalog,
    render_reducer_list,
)
from sciona.cli.render import render_reducer_show


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
    def __init__(self, module, category="structure"):
        self.module = module
        self.category = category


def test_format_reducer_call_includes_flags() -> None:
    call = format_reducer_call("dummy", _DummyReducer())
    assert call.startswith("reducer --id dummy")
    assert "--module-id MODULE_ID" in call
    assert "[--limit LIMIT]" in call
    assert "[--extras]" in call


def test_render_reducer_list_orders_roles() -> None:
    entries = [
        {
            "reducer_id": "b",
            "category": "metrics",
            "summary": "B",
        },
        {
            "reducer_id": "a",
            "category": "structure",
            "summary": "A",
        },
    ]
    reducers = {
        "a": _ReducerEntry(_DummyReducer(), "structure"),
        "b": _ReducerEntry(_DummyReducer(), "metrics"),
    }
    lines = render_reducer_list(entries, reducers, include_prefix=False)
    structure_index = lines.index("Category: structure")
    metrics_index = lines.index("Category: metrics")
    assert structure_index < metrics_index
    assert any(line.startswith("  Command: reducer --id a") for line in lines)
    assert "  Summary: A" in lines


def test_render_reducer_catalog_lists_entries() -> None:
    entries = [
        {
            "reducer_id": "alpha",
            "category": "structure",
            "summary": "Alpha",
        },
    ]
    lines = render_reducer_catalog(entries)
    assert "Available reducers:" in lines[0]
    assert "- alpha" in lines
    assert "  Summary: Alpha" in lines


def test_normalize_category_defaults_to_unknown() -> None:
    assert normalize_category("") == "unknown"
    assert normalize_category(" metrics ") == "metrics"


def test_render_reducer_show_includes_risk_and_stage() -> None:
    lines = render_reducer_show(
        {
            "reducer_id": "alpha",
            "category": "metrics",
            "placeholder": "ALPHA",
            "risk_tier": "elevated",
            "stage": "diagnostics_metrics",
            "summary": "Alpha.",
        }
    )
    assert "Category: metrics" in lines
    assert "Risk tier: elevated" in lines
    assert "Stage: diagnostics_metrics" in lines
    assert "Placeholder: ALPHA" in lines
