import sqlite3

from sciona.reducers.structural import structural_index
from sciona.runtime import constants as setup_config

from tests.helpers import seed_repo_with_snapshot


def test_structural_index_reducer_reports_modules_and_cycles(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    db_path = repo_root / setup_config.SCIONA_DIR_NAME / setup_config.DB_FILENAME
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    payload = structural_index.run(snapshot_id, conn=conn, repo_root=repo_root)
    conn.close()

    assert payload["projection"] == "structural_index"
    modules = payload["modules"]["entries"]
    assert modules[0]["module_id"] == "pkg.alpha"
    assert modules[0]["file_count"] == 2
    assert modules[0]["function_count"] == 1
    assert modules[0]["method_count"] == 1
    assert payload["files"]["count"] >= 2
    assert payload["classes"]["entries"][0]["qualified_name"].startswith("pkg.alpha")
    assert payload["functions"]["by_module"][0]["module_id"] == "pkg.alpha"
    edges = payload["imports"]["edges"]
    assert edges[0]["from_module_id"] <= edges[0]["to_module_id"]
    assert payload["import_cycles"][0]["modules"] == ["pkg.alpha", "pkg.beta"]
    file_entry = payload["files"]["entries"][0]
    assert set(file_entry.keys()) <= {"path", "module_id"}
