# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import sqlite3

from tests.helpers import Diagnostics, SnapshotDelta

from tests.helpers import setup_evolution_db


def _connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def test_snapshot_delta_reports_expected_changes(tmp_path):
    env = setup_evolution_db(tmp_path)
    conn = _connect(env["db_path"])
    delta = SnapshotDelta.compute(conn, env["snapshot_a"], env["snapshot_b"])
    conn.close()

    added_ids = {entry["structural_id"] for entry in delta.added_nodes}
    removed_ids = {entry["structural_id"] for entry in delta.removed_nodes}
    assert "mod_beta" in added_ids  # new module appears in snap_b only
    assert "func_new" in added_ids
    assert "func_old" in removed_ids  # retired helper disappears
    # Edge-level churn should include the new import edge from alpha->beta
    assert any(
        edge["src_structural_id"] == "mod_alpha"
        and edge["dst_structural_id"] == "mod_beta"
        for edge in delta.added_edges
    )


def test_diagnostics_flags_orphans_and_sets_health(tmp_path):
    env = setup_evolution_db(tmp_path)
    conn = _connect(env["db_path"])
    diagnostics = Diagnostics(conn).run(env["snapshot_b"], include_breakdown=True)
    conn.close()

    orphan_metrics = diagnostics.metrics["orphan_nodes"]
    assert orphan_metrics["count"] >= 1
    assert diagnostics.health == "degraded"
