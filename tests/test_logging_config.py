from sciona.runtime.config_io import write_default_config
from sciona.runtime.config import load_logging_settings
from sciona.runtime.paths import get_config_path


def test_logging_config_parsing(tmp_path):
    repo_root = tmp_path
    write_default_config(repo_root)
    config_path = get_config_path(repo_root)
    config_path.write_text(
        """logging:
  level: "WARNING"
  module_levels:
    sciona.code_analysis: "DEBUG"
    sciona.code_analysis.core.engine: "ERROR"
""",
        encoding="utf-8",
    )

    settings = load_logging_settings(repo_root)
    assert settings.level == "WARNING"
    assert settings.module_levels["sciona.code_analysis"] == "DEBUG"
    assert settings.module_levels["sciona.code_analysis.core.engine"] == "ERROR"
