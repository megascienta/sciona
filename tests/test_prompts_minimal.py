import sqlite3

from sciona.prompts import compile_prompt
from sciona.pipelines.prompts import ensure_prompts_initialized

from .helpers import seed_repo_with_snapshot


def test_compile_prompt_renders_core_prompt(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    ensure_prompts_initialized(repo_root)
    conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    conn.row_factory = sqlite3.Row
    try:
        prompt = compile_prompt(
            "preflight_v1",
            snapshot_id,
            conn,
            repo_root,
        )
    finally:
        conn.close()

    assert "PROMPT: preflight_v1" in prompt
    assert f"SNAPSHOT: {snapshot_id}" in prompt
    assert "SCIONA pre-flight" in prompt
