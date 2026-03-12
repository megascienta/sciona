# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.runtime.agents import setup as agents
from sciona.runtime.config.language_scope import tracked_extensions_for_enabled_names
from sciona.runtime.reducers.metadata import CATEGORY_ORDER
from sciona.reducers.registry import get_reducers


def test_agents_block_has_markers(tmp_path: Path):
    block = agents.build_agents_block(tmp_path, get_reducers())
    assert agents.BEGIN_MARKER in block
    assert agents.END_MARKER in block


def test_agents_upsert_append_and_remove(tmp_path: Path):
    target = tmp_path / agents.AGENTS_FILENAME
    target.write_text("Custom header\n", encoding="utf-8")
    agents.upsert_agents_file(tmp_path, mode="append", reducers=get_reducers())
    content = target.read_text(encoding="utf-8")
    assert "Custom header" in content
    assert agents.BEGIN_MARKER in content
    assert agents.END_MARKER in content

    removed = agents.remove_agents_block(tmp_path)
    assert removed is True
    cleaned = target.read_text(encoding="utf-8")
    assert "Custom header" in cleaned
    assert agents.BEGIN_MARKER not in cleaned


def test_agents_upsert_overwrite(tmp_path: Path):
    target = tmp_path / agents.AGENTS_FILENAME
    target.write_text("Old content\n", encoding="utf-8")
    agents.upsert_agents_file(tmp_path, mode="overwrite", reducers=get_reducers())
    content = target.read_text(encoding="utf-8")
    assert agents.BEGIN_MARKER in content
    assert "Old content" not in content


def test_investigation_role_categories_follow_category_order() -> None:
    rendered = agents._render_investigation_role_categories(get_reducers())
    headers = [
        line.strip("*:")
        for line in rendered.splitlines()
        if line.startswith("**") and line.endswith(":**")
    ]
    assert headers == [f"{category.capitalize()} reducers" for category in CATEGORY_ORDER]


def test_render_tracked_file_scope_uses_shared_language_scope(tmp_path: Path) -> None:
    sciona_dir = tmp_path / ".sciona"
    sciona_dir.mkdir()
    (sciona_dir / "config.yaml").write_text(
        "languages:\n"
        "  python:\n"
        "    enabled: true\n"
        "  javascript:\n"
        "    enabled: true\n",
        encoding="utf-8",
    )

    rendered = agents._render_tracked_file_scope(tmp_path)

    expected_extensions = ", ".join(
        sorted(tracked_extensions_for_enabled_names(["javascript", "python"]))
    )
    assert "- Enabled languages: javascript, python" in rendered
    assert f"- Tracked file types: {expected_extensions}" in rendered
