import shutil

from sciona.runtime.config_io import load_config_text, write_config_text
from sciona.runtime.paths import get_config_path, get_sciona_dir


def test_config_preservation_helpers(tmp_path):
    repo_root = tmp_path
    sciona_dir = get_sciona_dir(repo_root)
    sciona_dir.mkdir(parents=True, exist_ok=True)
    config_path = get_config_path(repo_root)
    config_path.write_text("custom: true\n", encoding="utf-8")

    saved = load_config_text(repo_root)
    assert saved == "custom: true\n"

    shutil.rmtree(sciona_dir)
    write_config_text(repo_root, saved or "")
    assert config_path.read_text(encoding="utf-8") == "custom: true\n"
