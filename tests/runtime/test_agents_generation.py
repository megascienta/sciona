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
    assert "6.2 Common usage" in block
    assert "6.1 Discovery" in block


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
        "{SCIONA_CONFIG_PATH}",
        "{COMMON_TASKS}",
        "{RISK_TIER_REDUCERS}",
        "{INVESTIGATION_STAGE_WORKFLOW}",
        "{INVESTIGATION_ROLE_CATEGORIES}",
        "{REDUCER_ESCALATION_ORDER}",
        "{CMD_VERSION}",
        "{CMD_INIT}",
        "{CMD_AGENTS}",
        "{CMD_REDUCER_LIST}",
        "{CMD_REDUCER_INFO}",
        "{CMD_REDUCER}",
        "{CMD_BUILD}",
        "{CMD_SEARCH}",
        "{CMD_RESOLVE}",
    }:
        assert token not in block
    assert "sciona --version" in block
    assert "sciona init" in block
    assert "sciona agents" in block
    assert "sciona reducer list" in block
    assert "sciona reducer info" in block
    assert "sciona reducer --id <reducer_id>" in block
    assert "sciona search" in block
    assert "sciona resolve" in block
    assert ".sciona/config.yaml" in block
    assert "Normal tier reducers:" in block
    assert "**Structure reducers:**" in block
    assert "Discovery and structural orientation" in block
    assert "Stage 1 — Initial scan" in block

def test_agents_block_section_order(tmp_path: Path):
    block = agents.build_agents_block(tmp_path, get_reducers())
    discovery = block.index("Discovery")
    common = block.index("Common usage")
    reporting = block.index("Reporting Checklist")
    troubleshooting = block.index("Troubleshooting")
    assert discovery < common < reporting < troubleshooting


def test_agents_block_removes_reviewed_template_issues(tmp_path: Path):
    block = agents.build_agents_block(tmp_path, get_reducers())
    template = Path("src/sciona/runtime/templates/agents_template.md").read_text(
        encoding="utf-8"
    )
    assert ".sciona/config`" not in block
    assert "§7.12" not in block
    assert 'Use "let me search the codebase for..." text search for structural information' not in block
    assert block.count("If SCIONA evidence is insufficient, agents MUST explicitly state what is missing and either:") == 1
    assert "Current reducer IDs by tier:\n\n- Normal tier reducers:" in block
    assert "{INVESTIGATION_STAGE_WORKFLOW}" not in block
    assert (
        "**Relations reducers:**\ncallsite_index, classifier_call_graph_summary, dependency_edges, module_call_graph_summary"
        in block
    )
    assert "Reducers: snapshot_provenance, structural_index" not in template
    assert "Role: structure." in block
