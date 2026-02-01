import shutil

from sciona.pipelines.config import public as config


def test_config_preservation_helpers(tmp_path):
    repo_root = tmp_path
    sciona_dir = config.get_sciona_dir(repo_root)
    sciona_dir.mkdir(parents=True, exist_ok=True)
    config_path = config.get_config_path(repo_root)
    config_path.write_text("custom: true\n", encoding="utf-8")

    saved = config.load_config_text(repo_root)
    assert saved == "custom: true\n"

    shutil.rmtree(sciona_dir)
    config.write_config_text(repo_root, saved or "")
    assert config_path.read_text(encoding="utf-8") == "custom: true\n"
