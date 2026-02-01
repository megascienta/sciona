from sciona.pipelines.config import public as config


def test_logging_config_parsing(tmp_path):
    repo_root = tmp_path
    config.write_default_config(repo_root)
    config_path = config.get_config_path(repo_root)
    config_path.write_text(
        """logging:
  level: "WARNING"
  module_levels:
    sciona.code_analysis: "DEBUG"
    sciona.code_analysis.core.engine: "ERROR"
""",
        encoding="utf-8",
    )

    settings = config.load_logging_settings(repo_root)
    assert settings.level == "WARNING"
    assert settings.module_levels["sciona.code_analysis"] == "DEBUG"
    assert settings.module_levels["sciona.code_analysis.core.engine"] == "ERROR"
