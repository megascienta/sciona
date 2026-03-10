# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Artifact build helpers for committed snapshots."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence, Set

from ...code_analysis import artifacts as artifact_derivation
from ...code_analysis.tools.call_extraction import CallExtractionRecord
from ...code_analysis.artifacts.engine import ArtifactEngine
from ...data_storage.connections import artifact
from ...data_storage.common.transactions import transaction
from ...data_storage.artifact_db.overlay import diff_overlay as overlay_store
from ...data_storage.artifact_db.overlay import diff_overlay_calls as overlay_call_store
from ...data_storage.artifact_db.overlay import (
    diff_overlay_summary as overlay_summary_store,
)
from ...data_storage.artifact_db.reporting import read_status as artifact_read
from ...data_storage.artifact_db.writes import write_index as artifact_write
from ...data_storage.core_db import read_ops as core_read
from ...data_storage.artifact_db.maintenance import rebuild_graph_index
from ...runtime.paths import get_artifact_db_path


def build_artifacts_for_snapshot(
    *,
    repo_root: Path,
    workspace_root: Path,
    conn,
    snapshot_id: str,
    languages,
    progress_factory=None,
    phase_reporter=None,
) -> tuple[Sequence[CallExtractionRecord], list[str]]:
    core_read.validate_snapshot_for_read(conn, snapshot_id, require_committed=True)
    artifacts_engine = ArtifactEngine(
        workspace_root,
        conn,
        languages=languages,
        config_root=repo_root,
        progress_factory=progress_factory,
    )
    call_artifacts = artifacts_engine.run(snapshot_id)
    warnings = list(artifacts_engine.warnings)
    refresh_artifact_state(
        repo_root=repo_root,
        conn=conn,
        snapshot_id=snapshot_id,
        call_artifacts=call_artifacts,
        progress_factory=progress_factory,
        phase_reporter=phase_reporter,
    )
    return call_artifacts, warnings


def refresh_artifact_state(
    *,
    repo_root: Path,
    conn,
    snapshot_id: str,
    call_artifacts: Sequence[CallExtractionRecord],
    progress_factory=None,
    phase_reporter=None,
) -> None:
    def _timed_phase(label: str, func):
        return func()

    current_node_ids = _timed_phase(
        "load_current_node_ids",
        lambda: set(core_read.snapshot_structural_ids(conn, snapshot_id)),
    )
    eligible_callers: Set[str] = set(current_node_ids)
    artifact_path = get_artifact_db_path(repo_root)
    with artifact(artifact_path, repo_root=repo_root) as artifact_conn:
        artifact_write.mark_rebuild_started(artifact_conn, snapshot_id=snapshot_id)
        artifact_write.reset_artifact_derived_state(artifact_conn)
        overlay_store.clear_all(artifact_conn)
        overlay_call_store.clear_all(artifact_conn)
        overlay_summary_store.clear_all(artifact_conn)
        artifact_conn.commit()
        try:
            with transaction(artifact_conn):
                call_resolution_diagnostics: dict[str, object] = {}
                _timed_phase(
                    "write_call_artifacts",
                    lambda: artifact_derivation.write_call_artifacts(
                        artifact_conn=artifact_conn,
                        core_conn=conn,
                        snapshot_id=snapshot_id,
                        call_records=call_artifacts,
                        eligible_callers=eligible_callers,
                        diagnostics=call_resolution_diagnostics,
                        progress_factory=progress_factory,
                    ),
                )
                artifact_write.set_rebuild_metadata(
                    artifact_conn,
                    key=f"call_resolution_diagnostics:{snapshot_id}",
                    value=json.dumps(call_resolution_diagnostics, sort_keys=True),
                )
                _timed_phase(
                    "rebuild_graph_index",
                    lambda: rebuild_graph_index(
                        artifact_conn,
                        core_conn=conn,
                        snapshot_id=snapshot_id,
                        progress_factory=progress_factory,
                    ),
                )
                _timed_phase(
                    "rebuild_graph_rollups",
                    lambda: artifact_derivation.rebuild_graph_rollups(
                        artifact_conn,
                        core_conn=conn,
                        snapshot_id=snapshot_id,
                        progress_factory=progress_factory,
                    ),
                )
            artifact_write.mark_rebuild_completed(
                artifact_conn, snapshot_id=snapshot_id
            )
            if not artifact_read.rebuild_consistent_for_snapshot(
                artifact_conn,
                snapshot_id=snapshot_id,
            ):
                raise RuntimeError(
                    f"Artifact rebuild status is inconsistent for snapshot {snapshot_id}."
                )
            artifact_conn.commit()
        except Exception:
            artifact_write.mark_rebuild_failed(artifact_conn, snapshot_id=snapshot_id)
            artifact_conn.commit()
            raise
