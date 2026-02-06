# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.pipelines import prompt as prompt_pipeline
from sciona.pipelines.prompts import ensure_prompts_initialized

from .helpers import seed_repo_with_snapshot


def test_compile_prompt_renders_core_prompt(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    ensure_prompts_initialized(repo_root)
    prompt, _ = prompt_pipeline.compile_prompt_by_name(
        "callable_impact_v1",
        repo_root=repo_root,
        arg_map={"callable_id": "pkg.alpha.service.helper"},
    )

    assert "PROMPT: callable_impact_v1" in prompt
    assert f"SNAPSHOT: {snapshot_id}" in prompt
    assert "SCIONA callable impact briefing" in prompt
