import json


def test_cli_prompt_json_includes_sections(cli_app_with_prompts, cli_runner):
    result = cli_runner.invoke(
        cli_app_with_prompts,
        [
            "prompt",
            "run",
            "preflight_v1",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "prompt" in payload
    assert "prompt_header" in payload
    assert "prompt_body" in payload
    assert "instructions" in payload
    assert "evidence" in payload
    assert "resolved_arg_map" in payload
    assert "PROMPT:" in (payload["prompt_header"] or "")
    assert "SCIONA pre-flight" in (payload["prompt_body"] or "")
