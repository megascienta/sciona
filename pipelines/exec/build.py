"""Build execution logic (mechanism only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

from ...runtime.logging import get_logger
from ...code_analysis.analysis.structural_hash import compute_structural_hash
from ...code_analysis.tools.call_extraction import CallExtractionRecord
from ...code_analysis.core import snapshot as snapshot_ingest
from ...code_analysis.core.engine import BuildEngine
from ..domain.policies import BuildPolicy
from ..domain.repository import RepoState
from ..domain.snapshots import SnapshotDecision, SnapshotLifecycle
from ...data_storage.connections import core
from ...data_storage.core_db import read_ops as core_read
from ...data_storage.core_db import write_ops as core_write
from ..build_artifacts import build_artifacts_for_snapshot
from ..progress import make_progress_factory

_LOGGER = get_logger("pipelines.exec.build")


@dataclass(frozen=True)
class BuildResult:
    files_processed: int
    nodes_recorded: int
    snapshot_id: str
    status: str
    call_artifacts: Sequence[CallExtractionRecord] = field(default_factory=list)
    enabled_languages: Sequence[str] = field(default_factory=list)
    discovery_counts: dict[str, int] = field(default_factory=dict)
    discovery_candidates: dict[str, int] = field(default_factory=dict)
    discovery_excluded_by_glob: dict[str, int] = field(default_factory=dict)
    discovery_excluded_total: int = 0
    exclude_globs: Sequence[str] = field(default_factory=list)
    parse_failures: int = 0
    analysis_warnings: Sequence[str] = field(default_factory=list)
    artifact_warnings: Sequence[str] = field(default_factory=list)


def build_repo(
    repo_state: RepoState,
    policy: BuildPolicy,
    *,
    workspace_root: Optional[Path] = None,
    source: str = "scan",
) -> BuildResult:
    workspace = workspace_root or repo_state.repo_root
    languages = policy.analysis.languages
    with core(repo_state.db_path, repo_root=repo_state.repo_root) as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            core_write.purge_uncommitted_snapshots(conn)
            baseline_meta = core_read.latest_committed_snapshot(conn)

            snapshot = snapshot_ingest.create_snapshot(workspace, source=source)
            engine = BuildEngine(
                workspace,
                conn,
                core_write,
                languages=languages,
                config_root=repo_state.repo_root,
                progress_factory=make_progress_factory(),
            )
            files_processed, node_count = engine.run(snapshot)
            structural_hash = compute_structural_hash(conn, snapshot.snapshot_id)
            enabled_languages = [
                name for name, settings in languages.items() if settings.enabled
            ]

            decision = _decide_snapshot(
                snapshot_id=snapshot.snapshot_id,
                structural_hash=structural_hash,
                baseline_meta=baseline_meta,
            )
            if decision.lifecycle == SnapshotLifecycle.REUSED and baseline_meta:
                if not core_read.snapshot_exists(conn, baseline_meta["snapshot_id"]):
                    decision = SnapshotDecision(
                        lifecycle=SnapshotLifecycle.COMMITTED,
                        snapshot_id=snapshot.snapshot_id,
                        structural_hash=structural_hash,
                        reason="baseline_missing",
                    )

            committed_snapshot_id = snapshot.snapshot_id
            status = SnapshotLifecycle.COMMITTED.value
            if decision.lifecycle == SnapshotLifecycle.REUSED and baseline_meta:
                core_write.delete_snapshot_tree(conn, snapshot.snapshot_id)
                core_write.delete_committed_snapshots_except(
                    conn, baseline_meta["snapshot_id"]
                )
                core_write.prune_orphan_structural_nodes(conn)
                committed_snapshot_id = baseline_meta["snapshot_id"]
                status = decision.lifecycle.value
            else:
                snapshot_ingest.persist_snapshot(
                    conn,
                    snapshot,
                    structural_hash,
                    is_committed=True,
                    store=core_write,
                )
                core_write.delete_committed_snapshots_except(conn, snapshot.snapshot_id)
                core_write.prune_orphan_structural_nodes(conn)
            conn.commit()
            call_artifacts: Sequence[CallExtractionRecord] = []
            artifact_warnings: Sequence[str] = []
            if policy.artifacts.refresh_artifacts:
                call_artifacts, artifact_warnings = build_artifacts_for_snapshot(
                    repo_root=repo_state.repo_root,
                    workspace_root=workspace,
                    conn=conn,
                    snapshot_id=committed_snapshot_id,
                    languages=languages,
                )
            return BuildResult(
                files_processed,
                node_count,
                committed_snapshot_id,
                status,
                call_artifacts=call_artifacts,
                enabled_languages=enabled_languages,
                discovery_counts=dict(engine.discovery_counts),
                discovery_candidates=dict(engine.discovery_candidates),
                discovery_excluded_by_glob=dict(engine.discovery_excluded_by_glob),
                discovery_excluded_total=engine.discovery_excluded_total,
                exclude_globs=list(engine.exclude_globs),
                parse_failures=engine.parse_failures,
                analysis_warnings=list(engine.warnings),
                artifact_warnings=list(artifact_warnings),
            )
        except Exception:
            if conn.in_transaction:
                conn.rollback()
            raise
        except BaseException:
            if conn.in_transaction:
                conn.rollback()
            raise


def _decide_snapshot(
    *,
    snapshot_id: str,
    structural_hash: str,
    baseline_meta,
) -> SnapshotDecision:
    if baseline_meta and baseline_meta.get("structural_hash") == structural_hash:
        return SnapshotDecision(
            lifecycle=SnapshotLifecycle.REUSED,
            snapshot_id=baseline_meta["snapshot_id"],
            structural_hash=structural_hash,
            reason="matching_baseline",
        )
    return SnapshotDecision(
        lifecycle=SnapshotLifecycle.COMMITTED,
        snapshot_id=snapshot_id,
        structural_hash=structural_hash,
        reason="new_snapshot",
    )


__all__ = [
    "BuildResult",
    "build_repo",
]
