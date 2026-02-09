# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.runtime import agents_setup as agents
from sciona.reducers.registry import get_reducers


def test_agents_block_has_markers(tmp_path: Path):
    block = agents.build_agents_block(tmp_path, get_reducers())
    assert agents.BEGIN_MARKER in block
    assert agents.END_MARKER in block
    assert "Tracked file scope" in block
    assert "Common reducer usage" in block
    assert "Reducer discovery" in block


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


def test_agents_block_expands_placeholders(tmp_path: Path):
    block = agents.build_agents_block(tmp_path, get_reducers())
    for token in {
        "{TRACKED_FILE_SCOPE}",
        "{COMMON_TASKS}",
        "{CMD_REDUCER_LIST}",
        "{CMD_REDUCER_INFO}",
        "{CMD_BUILD}",
        "{CMD_SEARCH}",
        "{CMD_RESOLVE}",
    }:
        assert token not in block
    assert "sciona reducer list" in block
    assert "sciona reducer info" in block
    assert "sciona search" in block
    assert "sciona resolve" in block
    assert "Evidence summary format" in block
    assert "Troubleshooting" in block


def test_agents_block_section_order(tmp_path: Path):
    block = agents.build_agents_block(tmp_path, get_reducers())
    discovery = block.index("### Reducer discovery")
    common = block.index("### Common reducer usage")
    reporting = block.index("### Reporting checklist")
    troubleshooting = block.index("### Troubleshooting")
    assert discovery < common < reporting < troubleshooting
