# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Build execution logic (mechanism only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from dataclasses import replace
import sqlite3
from pathlib import Path
from time import perf_counter
from typing import Optional, Sequence

from ...runtime.logging import get_logger
from ...code_analysis.analysis.structural_hash import compute_structural_hash
from ...code_analysis.tools.call_extraction import CallExtractionRecord
from ...code_analysis.core import snapshot as snapshot_ingest
from ...code_analysis.core.engine import BuildEngine
from ..domain.policies import BuildPolicy
from ..domain.repository import RepoState
from ..domain.snapshots import SnapshotDecision, SnapshotLifecycle
from ...data_storage.connections import artifact, artifact_readonly, core, core_readonly
from ...data_storage.artifact_db.reporting import read_status as artifact_read
from ...data_storage.artifact_db.writes import write_index as artifact_write
from ...data_storage.core_db import read_ops as core_read
from ...data_storage.core_db import write_ops as core_write
from ..build_artifacts import build_artifacts_for_snapshot
from ..progress import make_progress_factory
from .build_fingerprint import (
    compute_build_fingerprint,
    load_cached_build_result_payload,
    load_fingerprint_cache,
    write_fingerprint_cache,
)

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
    name_collisions_detected: int = 0
    name_collisions_disambiguated: int = 0
    residual_containment_failures: int = 0
    name_collisions_by_language: dict[str, dict[str, int]] = field(default_factory=dict)
    imports_seen: int = 0
    imports_internal: int = 0
    imports_filtered_not_internal: int = 0
    imports_by_language: dict[str, dict[str, int]] = field(default_factory=dict)
    analysis_warnings: Sequence[str] = field(default_factory=list)
    artifact_warnings: Sequence[str] = field(default_factory=list)


def build_repo(
    repo_state: RepoState,
    policy: BuildPolicy,
    *,
    workspace_root: Optional[Path] = None,
    source: str = "scan",
) -> BuildResult:
    started_at = perf_counter()
    workspace = workspace_root or repo_state.repo_root
    languages = policy.analysis.languages
    snapshot = snapshot_ingest.create_snapshot(workspace, source=source)
    fingerprint = compute_build_fingerprint(
        repo_state=repo_state,
        policy=policy,
        source=source,
        git_commit_sha=snapshot.git_commit_sha,
    )
    if not policy.force_rebuild:
        cached_result = _build_result_from_fingerprint_cache(
            repo_state=repo_state,
            policy=policy,
            fingerprint_hash=fingerprint.fingerprint_hash,
        )
        if cached_result is not None:
            _record_build_total_seconds(
                repo_state=repo_state,
                snapshot_id=cached_result.snapshot_id,
                total_build_seconds=perf_counter() - started_at,
            )
            return cached_result

    with core(repo_state.db_path, repo_root=repo_state.repo_root) as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            core_write.purge_uncommitted_snapshots(conn)
            baseline_meta = (
                None
                if policy.force_rebuild
                else core_read.latest_committed_snapshot(conn)
            )

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
            canonical_snapshot_id = snapshot_ingest.deterministic_snapshot_id(
                structural_hash=structural_hash,
                git_commit_sha=snapshot.git_commit_sha,
                source=snapshot.source,
            )

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
                committed_snapshot_id = baseline_meta["snapshot_id"]
                if committed_snapshot_id != canonical_snapshot_id:
                    if core_read.snapshot_exists(conn, canonical_snapshot_id):
                        core_write.delete_snapshot_tree(conn, canonical_snapshot_id)
                    core_write.rekey_snapshot_id(
                        conn,
                        from_snapshot_id=committed_snapshot_id,
                        to_snapshot_id=canonical_snapshot_id,
                    )
                    committed_snapshot_id = canonical_snapshot_id
                core_write.delete_committed_snapshots_except(conn, committed_snapshot_id)
                core_write.prune_orphan_structural_nodes(conn)
                core_write.prune_orphan_synthetic_nodes(conn)
                status = decision.lifecycle.value
            else:
                # CoreDB keeps a singleton committed snapshot. Remove older committed
                # rows before inserting the new committed snapshot metadata.
                core_write.delete_committed_snapshots_except(conn, canonical_snapshot_id)
                if core_read.snapshot_exists(conn, canonical_snapshot_id):
                    core_write.delete_snapshot_tree(conn, canonical_snapshot_id)
                core_write.rekey_snapshot_id(
                    conn,
                    from_snapshot_id=snapshot.snapshot_id,
                    to_snapshot_id=canonical_snapshot_id,
                )
                snapshot.snapshot_id = canonical_snapshot_id
                committed_snapshot_id = snapshot.snapshot_id
                snapshot_ingest.persist_snapshot(
                    conn,
                    snapshot,
                    structural_hash,
                    is_committed=True,
                    store=core_write,
                )
                core_write.delete_committed_snapshots_except(conn, snapshot.snapshot_id)
                core_write.prune_orphan_structural_nodes(conn)
                core_write.prune_orphan_synthetic_nodes(conn)
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
            result = BuildResult(
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
                name_collisions_detected=engine.name_collisions_detected,
                name_collisions_disambiguated=engine.name_collisions_disambiguated,
                residual_containment_failures=engine.residual_containment_failures,
                name_collisions_by_language=dict(engine.name_collisions_by_language),
                imports_seen=engine.imports_seen,
                imports_internal=engine.imports_internal,
                imports_filtered_not_internal=engine.imports_filtered_not_internal,
                imports_by_language=dict(engine.imports_by_language),
                analysis_warnings=list(engine.warnings),
                artifact_warnings=list(artifact_warnings),
            )
            write_fingerprint_cache(
                repo_state=repo_state,
                fingerprint=fingerprint,
                structural_hash=structural_hash,
                result_payload=_build_result_payload(result),
            )
            _record_build_total_seconds(
                repo_state=repo_state,
                snapshot_id=result.snapshot_id,
                total_build_seconds=perf_counter() - started_at,
            )
            return result
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


def _build_result_from_fingerprint_cache(
    *,
    repo_state: RepoState,
    policy: BuildPolicy,
    fingerprint_hash: str,
) -> BuildResult | None:
    cached = load_fingerprint_cache(repo_state)
    if not cached:
        return None
    if cached.get("fingerprint_hash") != fingerprint_hash:
        return None
    cached_snapshot_id = cached.get("snapshot_id")
    cached_structural_hash = cached.get("structural_hash")
    if not isinstance(cached_snapshot_id, str) or not cached_snapshot_id:
        return None
    if not isinstance(cached_structural_hash, str) or not cached_structural_hash:
        return None
    core_meta = _latest_committed_snapshot(repo_state)
    if not core_meta:
        return None
    if core_meta.get("snapshot_id") != cached_snapshot_id:
        return None
    if core_meta.get("structural_hash") != cached_structural_hash:
        return None
    if policy.artifacts.refresh_artifacts and not _artifacts_ready_for_snapshot(
        repo_state, cached_snapshot_id
    ):
        return None
    result_payload = load_cached_build_result_payload(cached)
    if not isinstance(result_payload, dict):
        return None
    hydrated = _hydrate_result_payload(result_payload)
    if hydrated is None:
        return None
    return replace(hydrated, status=SnapshotLifecycle.REUSED.value)


def _latest_committed_snapshot(repo_state: RepoState) -> dict[str, str] | None:
    try:
        with core_readonly(repo_state.db_path, repo_root=repo_state.repo_root) as conn:
            baseline = core_read.latest_committed_snapshot(conn)
            if baseline is None:
                return None
            return dict(baseline)
    except sqlite3.Error:
        return None


def _artifacts_ready_for_snapshot(repo_state: RepoState, snapshot_id: str) -> bool:
    try:
        with artifact_readonly(
            repo_state.artifact_db_path, repo_root=repo_state.repo_root
        ) as conn:
            return artifact_read.rebuild_consistent_for_snapshot(
                conn, snapshot_id=snapshot_id
            )
    except sqlite3.Error:
        return False


def _record_build_total_seconds(
    *,
    repo_state: RepoState,
    snapshot_id: str,
    total_build_seconds: float,
) -> None:
    with artifact(repo_state.artifact_db_path, repo_root=repo_state.repo_root) as conn:
        artifact_write.set_rebuild_metadata(
            conn,
            key=f"build_total_seconds:{snapshot_id}",
            value=f"{max(total_build_seconds, 0.0):.6f}",
        )
        conn.commit()


def _hydrate_result_payload(payload: dict[str, object]) -> BuildResult | None:
    try:
        return BuildResult(
            files_processed=int(payload["files_processed"]),
            nodes_recorded=int(payload["nodes_recorded"]),
            snapshot_id=str(payload["snapshot_id"]),
            status=str(payload["status"]),
            call_artifacts=[],
            enabled_languages=list(payload.get("enabled_languages", [])),
            discovery_counts=dict(payload.get("discovery_counts", {})),
            discovery_candidates=dict(payload.get("discovery_candidates", {})),
            discovery_excluded_by_glob=dict(payload.get("discovery_excluded_by_glob", {})),
            discovery_excluded_total=int(payload.get("discovery_excluded_total", 0)),
            exclude_globs=list(payload.get("exclude_globs", [])),
            parse_failures=int(payload.get("parse_failures", 0)),
            name_collisions_detected=int(
                payload.get("name_collisions_detected", 0)
            ),
            name_collisions_disambiguated=int(
                payload.get("name_collisions_disambiguated", 0)
            ),
            residual_containment_failures=int(
                payload.get("residual_containment_failures", 0)
            ),
            name_collisions_by_language=dict(
                payload.get("name_collisions_by_language", {})
            ),
            imports_seen=int(payload.get("imports_seen", 0)),
            imports_internal=int(payload.get("imports_internal", 0)),
            imports_filtered_not_internal=int(
                payload.get("imports_filtered_not_internal", 0)
            ),
            imports_by_language=dict(payload.get("imports_by_language", {})),
            analysis_warnings=list(payload.get("analysis_warnings", [])),
            artifact_warnings=list(payload.get("artifact_warnings", [])),
        )
    except Exception:
        return None


def _build_result_payload(result: BuildResult) -> dict[str, object]:
    return {
        "files_processed": result.files_processed,
        "nodes_recorded": result.nodes_recorded,
        "snapshot_id": result.snapshot_id,
        "status": result.status,
        "enabled_languages": list(result.enabled_languages),
        "discovery_counts": dict(result.discovery_counts),
        "discovery_candidates": dict(result.discovery_candidates),
        "discovery_excluded_by_glob": dict(result.discovery_excluded_by_glob),
        "discovery_excluded_total": result.discovery_excluded_total,
        "exclude_globs": list(result.exclude_globs),
        "parse_failures": result.parse_failures,
        "name_collisions_detected": result.name_collisions_detected,
        "name_collisions_disambiguated": result.name_collisions_disambiguated,
        "residual_containment_failures": result.residual_containment_failures,
        "name_collisions_by_language": dict(result.name_collisions_by_language),
        "imports_seen": result.imports_seen,
        "imports_internal": result.imports_internal,
        "imports_filtered_not_internal": result.imports_filtered_not_internal,
        "imports_by_language": dict(result.imports_by_language),
        "analysis_warnings": list(result.analysis_warnings),
        "artifact_warnings": list(result.artifact_warnings),
    }


__all__ = [
    "BuildResult",
    "build_repo",
]
