from sciona.data_storage.core_db import connect as db_connect
from sciona.runtime import constants as setup_config
from sciona.pipelines.config import public as config


def test_connect_enables_wal(tmp_path):
    repo_root = tmp_path
    sciona_dir = repo_root / setup_config.SCIONA_DIR_NAME
    sciona_dir.mkdir()

    conn = db_connect(config.get_db_path(repo_root), repo_root=repo_root)
    try:
        row = conn.execute("PRAGMA journal_mode").fetchone()
    finally:
        conn.close()

    assert row[0].lower() == "wal"
