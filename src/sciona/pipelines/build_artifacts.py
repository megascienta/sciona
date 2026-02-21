# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Artifact build helpers for committed snapshots."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Sequence, Set, Tuple

from ..code_analysis import artifacts as artifact_derivation
from ..code_analysis.tools.call_extraction import CallExtractionRecord
from ..code_analysis.artifacts.engine import ArtifactEngine
from ..code_analysis.core.annotate import diff as annotate_diff
from ..data_storage.connections import artifact
from ..data_storage.transactions import transaction
from ..data_storage.artifact_db import diff_overlay as overlay_store
from ..data_storage.artifact_db import diff_overlay_calls as overlay_call_store
from ..data_storage.artifact_db import diff_overlay_summary as overlay_summary_store
from ..data_storage.artifact_db import read_status as artifact_read
from ..data_storage.artifact_db import write_index as artifact_write
from ..data_storage.core_db import read_ops as core_read
from ..data_storage.artifact_db.maintenance_graph import rebuild_graph_index
from ..runtime.paths import get_artifact_db_path
from .progress import make_progress_factory


def build_artifacts_for_snapshot(
    *,
    repo_root: Path,
    workspace_root: Path,
    conn,
    snapshot_id: str,
    languages,
) -> tuple[Sequence[CallExtractionRecord], list[str]]:
    core_read.validate_snapshot_for_read(conn, snapshot_id, require_committed=True)
    artifacts_engine = ArtifactEngine(
        workspace_root,
        conn,
        languages=languages,
        config_root=repo_root,
        progress_factory=make_progress_factory(),
    )
    call_artifacts = artifacts_engine.run(snapshot_id)
    warnings = list(artifacts_engine.warnings)
    refresh_artifact_state(
        repo_root=repo_root,
        conn=conn,
        snapshot_id=snapshot_id,
        call_artifacts=call_artifacts,
    )
    return call_artifacts, warnings


def refresh_artifact_state(
    *,
    repo_root: Path,
    conn,
    snapshot_id: str,
    call_artifacts: Sequence[CallExtractionRecord],
) -> None:
    statuses, current_node_ids = _snapshot_nodes_status(conn, snapshot_id)
    current_statuses = [
        (node_id, status) for node_id, status in statuses if status != "removed"
    ]
    eligible_callers: Set[str] = {
        node_id for node_id, status in statuses if status in {"added", "modified"}
    }
    artifact_path = get_artifact_db_path(repo_root)
    with artifact(artifact_path, repo_root=repo_root) as artifact_conn:
        artifact_write.mark_rebuild_started(artifact_conn, snapshot_id=snapshot_id)
        overlay_store.clear_all(artifact_conn)
        overlay_call_store.clear_all(artifact_conn)
        overlay_summary_store.clear_all(artifact_conn)
        artifact_conn.commit()
        try:
            with transaction(artifact_conn):
                artifact_write.cleanup_removed_nodes(artifact_conn, current_node_ids)
                artifact_write.rewrite_node_status(
                    artifact_conn,
                    statuses=current_statuses,
                    producer_id=artifact_write.NODE_STATUS_PRODUCER,
                )
                artifact_derivation.write_call_artifacts(
                    artifact_conn=artifact_conn,
                    core_conn=conn,
                    snapshot_id=snapshot_id,
                    call_records=call_artifacts,
                    eligible_callers=eligible_callers,
                )
                rebuild_graph_index(
                    artifact_conn, core_conn=conn, snapshot_id=snapshot_id
                )
                artifact_derivation.rebuild_graph_rollups(
                    artifact_conn,
                    core_conn=conn,
                    snapshot_id=snapshot_id,
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


def _snapshot_nodes_status(
    conn, snapshot_id: str
) -> Tuple[List[Tuple[str, str]], Set[str]]:
    current_hashes = core_read.snapshot_node_hashes(conn, snapshot_id)
    previous_snapshot_id = annotate_diff.previous_snapshot_id(conn, snapshot_id)
    previous_hashes = previous_node_hashes(conn, previous_snapshot_id)
    statuses: List[Tuple[str, str]] = []
    current_ids: Set[str] = set()
    for structural_id, content_hash in current_hashes.items():
        current_ids.add(structural_id)
        statuses.append(
            (
                structural_id,
                classify_status(content_hash, previous_hashes.get(structural_id)),
            )
        )
    removed_ids = set(previous_hashes.keys()) - current_ids
    for structural_id in sorted(removed_ids):
        statuses.append((structural_id, "removed"))
    return statuses, current_ids


def previous_node_hashes(conn, snapshot_id: str | None) -> Dict[str, str]:
    if not snapshot_id:
        return {}
    return core_read.snapshot_node_hashes(conn, snapshot_id)


def classify_status(current_hash: str, previous_hash: str | None) -> str:
    if previous_hash is None:
        return "added"
    if previous_hash != current_hash:
        return "modified"
    return "unchanged"
