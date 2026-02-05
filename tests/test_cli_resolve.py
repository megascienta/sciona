

def test_cli_resolve_callable(cli_app, cli_runner):
    result = cli_runner.invoke(
        cli_app,
        ["resolve", "pkg.alpha.service.helper", "--kind", "callable"],
    )

    assert result.exit_code == 0
    assert "Resolved callable" in result.stdout
    assert "func_alpha" in result.stdout
