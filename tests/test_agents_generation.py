from pathlib import Path

from sciona.pipelines import agents


def test_agents_block_has_markers():
    block = agents.build_agents_block()
    assert agents.BEGIN_MARKER in block
    assert agents.END_MARKER in block
    assert "Common tasks" in block
    assert "Reducer discovery" in block


def test_agents_upsert_append_and_remove(tmp_path: Path):
    target = tmp_path / agents.AGENTS_FILENAME
    target.write_text("Custom header\n", encoding="utf-8")
    agents.upsert_agents_file(tmp_path, mode="append")
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
    agents.upsert_agents_file(tmp_path, mode="overwrite")
    content = target.read_text(encoding="utf-8")
    assert agents.BEGIN_MARKER in content
    assert "Old content" not in content
