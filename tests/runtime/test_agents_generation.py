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


def test_agents_block_tracked_scope_uses_registry_extensions(tmp_path: Path):
    sciona_dir = tmp_path / ".sciona"
    sciona_dir.mkdir()
    (sciona_dir / "config.yaml").write_text(
        "\n".join(
            [
                "languages:",
                "  javascript:",
                "    enabled: true",
                "  python:",
                "    enabled: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    block = agents.build_agents_block(tmp_path, get_reducers())
    assert "- Enabled languages: javascript, python" in block
    assert "- Tracked file types: .cjs, .js, .mjs, .py" in block


def test_agents_block_expands_placeholders(tmp_path: Path):
    block = agents.build_agents_block(tmp_path, get_reducers())
    for token in {
        "{TRACKED_FILE_SCOPE}",
        "{SCIONA_CONFIG_PATH}",
        "{COMMON_TASKS}",
        "{RISK_TIER_REDUCERS}",
        "{INVESTIGATION_STAGE_WORKFLOW}",
        "{INVESTIGATION_ROLE_CATEGORIES}",
        "{SOURCE_REDUCER_LIST}",
        "{ANOMALY_DETECTOR_LIST}",
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
    assert "--json" in block
    assert ".sciona/config.yaml" in block
    assert "Normal tier reducers:" in block
    assert "**Structure reducers:**" in block
    assert "- `callable_source`" in block
    assert "- `concatenated_source`" in block
    assert "- `call_resolution_quality`" in block
    assert "- `hotspot_summary`" in block
    assert "- `structural_integrity_summary`" in block
    assert "Initial scan" in block
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
    assert "{SOURCE_REDUCER_LIST}" not in block
    assert "{ANOMALY_DETECTOR_LIST}" not in block
    assert "Reducers COULD be discovered via:" not in block
    assert "Reducers MAY be discovered via:" in block
    assert "Agents MUST NOT append `--json` to reducer commands." in block
    assert (
        "This prohibition applies to `sciona reducer` commands only. `--json` is valid on `sciona search` and `sciona resolve`."
        in block
    )
    assert (
        "**Relations reducers:**\ncallsite_index, classifier_call_graph_summary, dependency_edges, module_call_graph_summary, symbol_references"
        in block
    )
    assert "unverified: pending reducer confirmation" not in block
    assert "unverified: no reducer evidence" not in block
    assert "Raise an evidence-bounded concern under §2.7" in block
    assert "Cross-category verification is governed by §7.3" in block
    assert "DO: `sciona search" in block
    assert "Reducers: snapshot_provenance, structural_index" not in template
    assert "- `callable_source`\n- `concatenated_source`" not in template
    assert "- `structural_integrity_summary`\n- `hotspot_summary`\n- `call_resolution_quality`" not in template
    assert "Stage 1 — Initial scan\n  Purpose: orient to snapshot state and identify scope\n  Reducers: snapshot_provenance, structural_index" in block
    assert "Stage 2 — Entity discovery\n  Purpose: resolve unknown identifiers; locate symbols\n  Reducers: file_outline, module_overview, symbol_lookup" in block
    assert "structure reducer → relations reducer → diagnostics reducer" in block
    assert "Role: structure." in block
    assert "Role: relations." in block
