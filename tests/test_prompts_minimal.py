from sciona.pipelines import prompt as prompt_pipeline
from sciona.pipelines.prompts import ensure_prompts_initialized

from .helpers import seed_repo_with_snapshot


def test_compile_prompt_renders_core_prompt(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    ensure_prompts_initialized(repo_root)
    prompt, _ = prompt_pipeline.compile_prompt_by_name("preflight_v1", repo_root=repo_root)

    assert "PROMPT: preflight_v1" in prompt
    assert f"SNAPSHOT: {snapshot_id}" in prompt
    assert "SCIONA pre-flight" in prompt
