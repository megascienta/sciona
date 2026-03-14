# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Build execution logic (mechanism only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from dataclasses import replace
import json
import sqlite3
from pathlib import Path
from time import perf_counter
from typing import Optional, Sequence

from ...runtime.logging import get_logger
from ...code_analysis.diagnostics.pre_persist import report as diagnostic_report
from ...code_analysis.diagnostics.pre_persist.pipeline import (
    classify_pre_persist_misses,
)
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
from ..ops.build_artifacts import build_artifacts_for_snapshot
from ..progress import make_build_progress
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
    health: str = "ok"
    call_artifacts: Sequence[CallExtractionRecord] = field(default_factory=list)
    enabled_languages: Sequence[str] = field(default_factory=list)
    discovery_counts: dict[str, int] = field(default_factory=dict)
    discovery_candidates: dict[str, int] = field(default_factory=dict)
    discovery_excluded_by_glob: dict[str, int] = field(default_factory=dict)
    discovery_excluded_total: int = 0
    exclude_globs: Sequence[str] = field(default_factory=list)
    parse_failures: int = 0
    parse_files_with_diagnostics: int = 0
    parse_error_nodes: int = 0
    parse_significant_missing_nodes: int = 0
    name_collisions_detected: int = 0
    name_collisions_disambiguated: int = 0
    residual_containment_failures: int = 0
    parse_diagnostics_by_language: dict[str, dict[str, int]] = field(default_factory=dict)
    name_collisions_by_language: dict[str, dict[str, int]] = field(default_factory=dict)
    imports_seen: int = 0
    imports_internal: int = 0
    imports_filtered_not_internal: int = 0
    imports_by_language: dict[str, dict[str, int]] = field(default_factory=dict)
    analysis_warnings: Sequence[str] = field(default_factory=list)
    artifact_warnings: Sequence[str] = field(default_factory=list)
    diagnostic_report: dict[str, object] | None = None
    diagnostic_verbose: dict[str, object] | None = None


def build_repo(
    repo_state: RepoState,
    policy: BuildPolicy,
    *,
    workspace_root: Optional[Path] = None,
    source: str = "scan",
    diagnostic: bool = False,
    diagnostic_verbose: bool = False,
) -> BuildResult:
    started_at = perf_counter()
    build_progress = make_build_progress(total_steps=11 if diagnostic else 10)
    phase_reporter = build_progress.emit_phase
    progress_factory = build_progress.make_progress_factory()
    workspace = workspace_root or repo_state.repo_root
    languages = policy.analysis.languages
    snapshot = snapshot_ingest.create_snapshot(workspace, source=source)
    phase_reporter("Computing build fingerprint")
    fingerprint = compute_build_fingerprint(
        repo_state=repo_state,
        policy=policy,
        source=source,
        git_commit_sha=snapshot.git_commit_sha,
    )
    reused_result = _maybe_reuse_build_result(
        repo_state=repo_state,
        policy=policy,
        fingerprint_hash=fingerprint.fingerprint_hash,
    )
    if reused_result is not None:
        build_progress.finalize()
        return reused_result

    with core(repo_state.db_path, repo_root=repo_state.repo_root) as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            core_write.purge_uncommitted_snapshots(conn)

            engine = BuildEngine(
                workspace,
                conn,
                core_write,
                languages=languages,
                config_root=repo_state.repo_root,
                progress_factory=progress_factory,
                phase_reporter=phase_reporter,
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

            # Every build fully replaces snapshot-scoped committed state.
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
            diagnostic_payload: dict[str, object] | None = None
            if policy.artifacts.refresh_artifacts:
                call_artifacts, artifact_warnings = build_artifacts_for_snapshot(
                    repo_root=repo_state.repo_root,
                    workspace_root=workspace,
                    conn=conn,
                    snapshot_id=committed_snapshot_id,
                    languages=languages,
                    progress_factory=progress_factory,
                    phase_reporter=phase_reporter,
                )
            if diagnostic:
                if call_artifacts:
                    with diagnostic_report.diagnostic_workspace(repo_state.sciona_dir):
                        diagnostic_payload = classify_pre_persist_misses(
                            core_conn=conn,
                            snapshot_id=committed_snapshot_id,
                            call_records=call_artifacts,
                            progress_factory=progress_factory,
                        )
                else:
                    phase_reporter("Diagnostic classification")
                    with diagnostic_report.diagnostic_workspace(repo_state.sciona_dir):
                        diagnostic_payload = classify_pre_persist_misses(
                            core_conn=conn,
                            snapshot_id=committed_snapshot_id,
                            call_records=call_artifacts,
                        )
            result = BuildResult(
                files_processed,
                node_count,
                committed_snapshot_id,
                SnapshotLifecycle.COMMITTED.value,
                health="degraded" if engine.parse_failures else "ok",
                call_artifacts=call_artifacts,
                enabled_languages=enabled_languages,
                discovery_counts=dict(engine.discovery_counts),
                discovery_candidates=dict(engine.discovery_candidates),
                discovery_excluded_by_glob=dict(engine.discovery_excluded_by_glob),
                discovery_excluded_total=engine.discovery_excluded_total,
                exclude_globs=list(engine.exclude_globs),
                parse_failures=engine.parse_failures,
                parse_files_with_diagnostics=engine.parse_files_with_diagnostics,
                parse_error_nodes=engine.parse_error_nodes,
                parse_significant_missing_nodes=engine.parse_significant_missing_nodes,
                name_collisions_detected=engine.name_collisions_detected,
                name_collisions_disambiguated=engine.name_collisions_disambiguated,
                residual_containment_failures=engine.residual_containment_failures,
                parse_diagnostics_by_language=dict(engine.parse_diagnostics_by_language),
                name_collisions_by_language=dict(engine.name_collisions_by_language),
                imports_seen=engine.imports_seen,
                imports_internal=engine.imports_internal,
                imports_filtered_not_internal=engine.imports_filtered_not_internal,
                imports_by_language=dict(engine.imports_by_language),
                analysis_warnings=list(engine.warnings),
                artifact_warnings=list(artifact_warnings),
                diagnostic_report=diagnostic_payload,
                diagnostic_verbose=(
                    diagnostic_report.build_verbose_payload(diagnostic_payload)
                    if diagnostic_verbose and diagnostic_payload is not None
                    else None
                ),
            )
            write_fingerprint_cache(
                repo_state=repo_state,
                fingerprint=fingerprint,
                structural_hash=structural_hash,
                result_payload=_build_result_payload(result),
            )
            build_progress.finalize()
            _record_build_metrics(
                repo_state=repo_state,
                snapshot_id=result.snapshot_id,
                total_build_seconds=perf_counter() - started_at,
                phase_timings=build_progress.phase_timings(),
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


def _maybe_reuse_build_result(
    *,
    repo_state: RepoState,
    policy: BuildPolicy,
    fingerprint_hash: str,
) -> BuildResult | None:
    if policy.force_rebuild:
        return None
    cached_payload = load_fingerprint_cache(repo_state)
    if not isinstance(cached_payload, dict):
        return None
    if cached_payload.get("fingerprint_hash") != fingerprint_hash:
        return None
    result_payload = load_cached_build_result_payload(cached_payload)
    if result_payload is None:
        return None
    cached_result = _hydrate_result_payload(result_payload)
    if cached_result is None:
        return None
    with core_readonly(repo_state.db_path, repo_root=repo_state.repo_root) as conn:
        if not core_read.snapshot_exists(conn, cached_result.snapshot_id):
            return None
    return replace(cached_result, status=SnapshotLifecycle.REUSED.value)


def _record_build_metrics(
    *,
    repo_state: RepoState,
    snapshot_id: str,
    total_build_seconds: float,
    phase_timings: dict[str, float] | None = None,
) -> None:
    with artifact(repo_state.artifact_db_path, repo_root=repo_state.repo_root) as conn:
        artifact_write.set_rebuild_metadata(
            conn,
            key=f"build_total_seconds:{snapshot_id}",
            value=f"{max(total_build_seconds, 0.0):.6f}",
        )
        if phase_timings is not None:
            artifact_write.set_rebuild_metadata(
                conn,
                key=f"build_phase_timings:{snapshot_id}",
                value=json.dumps(phase_timings, sort_keys=True),
            )
        conn.commit()


def record_build_wall_seconds(
    *,
    repo_state: RepoState,
    snapshot_id: str,
    wall_seconds: float,
) -> None:
    with artifact(repo_state.artifact_db_path, repo_root=repo_state.repo_root) as conn:
        artifact_write.set_rebuild_metadata(
            conn,
            key=f"build_wall_seconds:{snapshot_id}",
            value=f"{max(wall_seconds, 0.0):.6f}",
        )
        conn.commit()


def _hydrate_result_payload(payload: dict[str, object]) -> BuildResult | None:
    try:
        return BuildResult(
            files_processed=int(payload["files_processed"]),
            nodes_recorded=int(payload["nodes_recorded"]),
            snapshot_id=str(payload["snapshot_id"]),
            status=str(payload["status"]),
            health=str(payload.get("health", "ok")),
            call_artifacts=[],
            enabled_languages=list(payload.get("enabled_languages", [])),
            discovery_counts=dict(payload.get("discovery_counts", {})),
            discovery_candidates=dict(payload.get("discovery_candidates", {})),
            discovery_excluded_by_glob=dict(payload.get("discovery_excluded_by_glob", {})),
            discovery_excluded_total=int(payload.get("discovery_excluded_total", 0)),
            exclude_globs=list(payload.get("exclude_globs", [])),
            parse_failures=int(payload.get("parse_failures", 0)),
            parse_files_with_diagnostics=int(
                payload.get("parse_files_with_diagnostics", 0)
            ),
            parse_error_nodes=int(payload.get("parse_error_nodes", 0)),
            parse_significant_missing_nodes=int(
                payload.get("parse_significant_missing_nodes", 0)
            ),
            name_collisions_detected=int(
                payload.get("name_collisions_detected", 0)
            ),
            name_collisions_disambiguated=int(
                payload.get("name_collisions_disambiguated", 0)
            ),
            residual_containment_failures=int(
                payload.get("residual_containment_failures", 0)
            ),
            parse_diagnostics_by_language=dict(
                payload.get("parse_diagnostics_by_language", {})
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
        "health": result.health,
        "enabled_languages": list(result.enabled_languages),
        "discovery_counts": dict(result.discovery_counts),
        "discovery_candidates": dict(result.discovery_candidates),
        "discovery_excluded_by_glob": dict(result.discovery_excluded_by_glob),
        "discovery_excluded_total": result.discovery_excluded_total,
        "exclude_globs": list(result.exclude_globs),
        "parse_failures": result.parse_failures,
        "parse_files_with_diagnostics": result.parse_files_with_diagnostics,
        "parse_error_nodes": result.parse_error_nodes,
        "parse_significant_missing_nodes": result.parse_significant_missing_nodes,
        "name_collisions_detected": result.name_collisions_detected,
        "name_collisions_disambiguated": result.name_collisions_disambiguated,
        "residual_containment_failures": result.residual_containment_failures,
        "parse_diagnostics_by_language": dict(result.parse_diagnostics_by_language),
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
