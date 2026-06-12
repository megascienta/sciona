# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.runtime.agents import claude_setup as claude
from sciona.runtime.agents._block_utils import BEGIN_MARKER, END_MARKER
from sciona.runtime.config.language_scope import tracked_extensions_for_enabled_names
from sciona.runtime.reducers.metadata import CATEGORY_ORDER
from sciona.reducers.registry import get_reducers


def test_claude_block_has_markers(tmp_path: Path):
    block = claude.build_claude_block(tmp_path, get_reducers())
    assert BEGIN_MARKER in block
    assert END_MARKER in block


def test_claude_block_exposes_markers_as_module_constants(tmp_path: Path):
    block = claude.build_claude_block(tmp_path, get_reducers())
    assert claude.BEGIN_MARKER in block
    assert claude.END_MARKER in block


def test_claude_upsert_append_and_remove(tmp_path: Path):
    target = tmp_path / claude.CLAUDE_FILENAME
    target.write_text("Custom header\n", encoding="utf-8")
    claude.upsert_claude_file(tmp_path, mode="append", reducers=get_reducers())
    content = target.read_text(encoding="utf-8")
    assert "Custom header" in content
    assert BEGIN_MARKER in content
    assert END_MARKER in content

    removed = claude.remove_claude_block(tmp_path)
    assert removed is True
    cleaned = target.read_text(encoding="utf-8")
    assert "Custom header" in cleaned
    assert BEGIN_MARKER not in cleaned


def test_claude_upsert_overwrite(tmp_path: Path):
    target = tmp_path / claude.CLAUDE_FILENAME
    target.write_text("Old content\n", encoding="utf-8")
    claude.upsert_claude_file(tmp_path, mode="overwrite", reducers=get_reducers())
    content = target.read_text(encoding="utf-8")
    assert BEGIN_MARKER in content
    assert "Old content" not in content


def test_claude_upsert_creates_file_when_absent(tmp_path: Path):
    target = tmp_path / claude.CLAUDE_FILENAME
    assert not target.exists()
    claude.upsert_claude_file(tmp_path, mode="append", reducers=get_reducers())
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert BEGIN_MARKER in content


def test_claude_remove_returns_false_when_no_file(tmp_path: Path):
    assert claude.remove_claude_block(tmp_path) is False


def test_claude_remove_returns_false_when_no_markers(tmp_path: Path):
    target = tmp_path / claude.CLAUDE_FILENAME
    target.write_text("Some content without markers\n", encoding="utf-8")
    assert claude.remove_claude_block(tmp_path) is False


def test_claude_remove_deletes_file_when_only_block(tmp_path: Path):
    target = tmp_path / claude.CLAUDE_FILENAME
    claude.upsert_claude_file(tmp_path, mode="overwrite", reducers=get_reducers())
    assert target.exists()
    removed = claude.remove_claude_block(tmp_path)
    assert removed is True
    assert not target.exists()


def test_claude_upsert_idempotent(tmp_path: Path):
    claude.upsert_claude_file(tmp_path, mode="append", reducers=get_reducers())
    first = (tmp_path / claude.CLAUDE_FILENAME).read_text(encoding="utf-8")
    claude.upsert_claude_file(tmp_path, mode="append", reducers=get_reducers())
    second = (tmp_path / claude.CLAUDE_FILENAME).read_text(encoding="utf-8")
    assert first == second


def test_investigation_role_categories_follow_category_order() -> None:
    rendered = claude._render_investigation_role_categories(get_reducers())
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

    rendered = claude._render_tracked_file_scope(tmp_path)

    expected_extensions = ", ".join(
        sorted(tracked_extensions_for_enabled_names(["javascript", "python"]))
    )
    assert "- Enabled languages: javascript, python" in rendered
    assert f"- Tracked file types: {expected_extensions}" in rendered


def test_claude_upsert_raises_on_symlink(tmp_path: Path) -> None:
    target = tmp_path / claude.CLAUDE_FILENAME
    other = tmp_path / "other.md"
    other.write_text("original\n", encoding="utf-8")
    target.symlink_to(other)
    import pytest
    with pytest.raises(ValueError, match="symbolic link"):
        claude.upsert_claude_file(tmp_path, mode="append", reducers=get_reducers())
    assert other.read_text(encoding="utf-8") == "original\n"


def test_claude_remove_raises_on_symlink(tmp_path: Path) -> None:
    target = tmp_path / claude.CLAUDE_FILENAME
    other = tmp_path / "other.md"
    other.write_text(f"{BEGIN_MARKER}\ncontent\n{END_MARKER}\n", encoding="utf-8")
    target.symlink_to(other)
    import pytest
    with pytest.raises(ValueError, match="symbolic link"):
        claude.remove_claude_block(tmp_path)


def test_claude_block_contains_claude_code_idioms(tmp_path: Path) -> None:
    block = claude.build_claude_block(tmp_path, get_reducers())
    assert "Bash" in block
    assert "Read" in block
    assert "Claude Code" in block


def test_claude_block_command_placeholders_filled(tmp_path: Path) -> None:
    commands = {
        "init": "sciona init",
        "claude": "sciona claude",
        "build": "sciona build",
    }
    block = claude.build_claude_block(tmp_path, get_reducers(), commands=commands)
    assert "sciona init" in block
    assert "sciona claude" in block
    assert "sciona build" in block
    assert "{CMD_INIT}" not in block
    assert "{CMD_CLAUDE}" not in block
    assert "{CMD_BUILD}" not in block


def test_claude_block_contains_generated_reducer_usage_notes(tmp_path: Path) -> None:
    block = claude.build_claude_block(tmp_path, get_reducers())

    assert "Reducer argument vocabulary:" in block
    assert "`dependency_edges`" in block
    assert "`--direction DIRECTION`: str; optional; one of: in, out, both; default: both" in block
    assert "`--compact`: bool; optional; default: false" in block
