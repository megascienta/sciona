# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.runtime.reducer_listing import (
    format_investigation_roles,
    format_reducer_call,
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
    def __init__(self, module, investigation_roles=()):
        self.module = module
        self.investigation_roles = investigation_roles


def test_format_reducer_call_includes_flags() -> None:
    call = format_reducer_call("dummy", _DummyReducer())
    assert call.startswith("reducer --id dummy")
    assert "--module-id MODULE_ID" in call
    assert "[--limit LIMIT]" in call
    assert "[--extras]" in call


def test_render_reducer_list_orders_categories() -> None:
    entries = [
        {
            "reducer_id": "b",
            "category": "analytics",
            "summary": "B",
            "investigation_roles": ["metrics"],
        },
        {
            "reducer_id": "a",
            "category": "core",
            "summary": "A",
            "investigation_roles": ["structure"],
        },
    ]
    reducers = {
        "a": _ReducerEntry(_DummyReducer(), ("structure",)),
        "b": _ReducerEntry(_DummyReducer(), ("metrics",)),
    }
    lines = render_reducer_list(entries, reducers, include_prefix=False)
    core_index = lines.index("Category: core")
    analytics_index = lines.index("Category: analytics")
    assert core_index < analytics_index
    assert any(line.startswith("  Command: reducer --id a") for line in lines)
    assert any("Role: structure." in line for line in lines)


def test_render_reducer_catalog_lists_entries() -> None:
    entries = [
        {
            "reducer_id": "alpha",
            "category": "core",
            "summary": "Alpha",
            "investigation_roles": ["structure", "relations"],
        },
    ]
    lines = render_reducer_catalog(entries)
    assert "Available reducers:" in lines[0]
    assert "- alpha" in lines
    assert any("Role: structure, relations." in line for line in lines)


def test_format_investigation_roles_uses_declared_order() -> None:
    assert format_investigation_roles(["source", "metrics", "structure"]) == (
        "structure, metrics, source"
    )


def test_render_reducer_show_includes_risk_and_stage() -> None:
    lines = render_reducer_show(
        {
            "reducer_id": "alpha",
            "scope": "codebase",
            "category": "analytics",
            "investigation_roles": ["metrics"],
            "risk_tier": "elevated",
            "investigation_stage": "analytical_relations_metrics",
            "determinism": "conditional",
            "summary": "Alpha.",
        }
    )
    assert "Role: metrics" in lines
    assert "Risk tier: elevated" in lines
    assert "Investigation stage: analytical_relations_metrics" in lines
