"""Build execution logic (mechanism only)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shutil
from typing import List, Optional, Sequence

from ...runtime.logging import get_logger
from ...code_analysis.analysis.structural_hash import compute_structural_hash
from ...code_analysis.tools.call_extraction import CallExtractionRecord
from ...code_analysis.core import snapshot as snapshot_ingest
from ...code_analysis.core.engine import BuildEngine
from ...runtime import git as git_ops
from ...runtime.policies import BuildPolicy
from ...runtime.repo_state import RepoState
from ...runtime.snapshots import SnapshotDecision, SnapshotLifecycle
from ...data_storage.connections import core
from ...data_storage.core_db import store as core_store
from .. import snapshot_policy
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


def build_repo(
    repo_state: RepoState,
    policy: BuildPolicy,
    *,
    workspace_root: Optional[Path] = None,
    source: str = "scan",
    run_addon_hooks: bool = True,
) -> BuildResult:
    workspace = workspace_root or repo_state.repo_root
    languages = policy.analysis.languages
    with core(repo_state.db_path, repo_root=repo_state.repo_root) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            core_store.purge_uncommitted_snapshots(conn)
            baseline_meta = core_store.latest_committed_snapshot(conn)

            snapshot = snapshot_ingest.create_snapshot(workspace, source=source)
            engine = BuildEngine(
                workspace,
                conn,
                core_store,
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
                if not core_store.snapshot_exists(conn, baseline_meta["snapshot_id"]):
                    decision = SnapshotDecision(
                        lifecycle=SnapshotLifecycle.COMMITTED,
                        snapshot_id=snapshot.snapshot_id,
                        structural_hash=structural_hash,
                        reason="baseline_missing",
                    )

            if decision.lifecycle == SnapshotLifecycle.REUSED and baseline_meta:
                core_store.delete_snapshot_tree(conn, snapshot.snapshot_id)
                call_artifacts: Sequence[CallExtractionRecord] = []
                if policy.artifacts.refresh_artifacts:
                    call_artifacts = build_artifacts_for_snapshot(
                        repo_root=repo_state.repo_root,
                        workspace_root=workspace,
                        conn=conn,
                        snapshot_id=baseline_meta["snapshot_id"],
                        languages=languages,
                        run_addon_hooks=run_addon_hooks,
                    )
                conn.commit()
                return BuildResult(
                    files_processed,
                    node_count,
                    baseline_meta["snapshot_id"],
                    decision.lifecycle.value,
                    call_artifacts=call_artifacts,
                    enabled_languages=enabled_languages,
                    discovery_counts=dict(engine.discovery_counts),
                    discovery_candidates=dict(engine.discovery_candidates),
                    discovery_excluded_by_glob=dict(engine.discovery_excluded_by_glob),
                    discovery_excluded_total=engine.discovery_excluded_total,
                    exclude_globs=list(engine.exclude_globs),
                    parse_failures=engine.parse_failures,
                )

            snapshot_ingest.persist_snapshot(
                conn,
                snapshot,
                structural_hash,
                is_committed=True,
                store=core_store,
            )
            snapshot_policy.rotate_committed_snapshots(conn, policy.analysis.snapshot_policy.retention_committed)
            call_artifacts: Sequence[CallExtractionRecord] = []
            if policy.artifacts.refresh_artifacts:
                call_artifacts = build_artifacts_for_snapshot(
                    repo_root=repo_state.repo_root,
                    workspace_root=workspace,
                    conn=conn,
                    snapshot_id=snapshot.snapshot_id,
                    languages=languages,
                    run_addon_hooks=run_addon_hooks,
                )
            conn.commit()
            return BuildResult(
                files_processed,
                node_count,
                snapshot.snapshot_id,
                SnapshotLifecycle.COMMITTED.value,
                call_artifacts=call_artifacts,
                enabled_languages=enabled_languages,
                discovery_counts=dict(engine.discovery_counts),
                discovery_candidates=dict(engine.discovery_candidates),
                discovery_excluded_by_glob=dict(engine.discovery_excluded_by_glob),
                discovery_excluded_total=engine.discovery_excluded_total,
                exclude_globs=list(engine.exclude_globs),
                parse_failures=engine.parse_failures,
            )
        except Exception:
            conn.rollback()
            raise
        except BaseException:
            conn.rollback()
            raise


def seed_initial_snapshots(repo_state: RepoState, policy: BuildPolicy, dirty_tree: bool) -> None:
    sciona_dir = repo_state.sciona_dir
    if not sciona_dir.exists():
        return
    with core(repo_state.db_path, repo_root=repo_state.repo_root) as conn:
        has_committed = conn.execute(
            "SELECT 1 FROM snapshots WHERE is_committed = 1 LIMIT 1"
        ).fetchone()
        if has_committed:
            return
    window = max(policy.analysis.snapshot_policy.retention_committed, 1)
    commits_needed = window if dirty_tree else max(window - 1, 0)
    commits_needed = min(commits_needed, policy.analysis.bootstrap_policy.max_commits)
    if commits_needed <= 0:
        return
    limit = max(1, min(policy.analysis.bootstrap_policy.max_commits + 1, commits_needed + 1))
    commits = list_bootstrap_commits(
        repo_state.repo_root,
        limit,
        policy.analysis.bootstrap_policy.max_days,
    )
    if not commits:
        return
    head_sha = commits[-1]
    historical = [sha for sha in commits if sha != head_sha]
    if not historical:
        return
    commits_to_run = historical[-commits_needed:]
    if not commits_to_run:
        return
    _LOGGER.info("Seeding %s snapshot(s) from git history...", len(commits_to_run))
    run_bootstrap_builds(repo_state, policy, commits_to_run, verbose=False)


def run_bootstrap_builds(
    repo_state: RepoState,
    policy: BuildPolicy,
    commits: List[str],
    verbose: bool = False,
) -> None:
    if not commits:
        return
    worktree_path = _prepare_bootstrap_worktree(repo_state.repo_root, repo_state.sciona_dir)
    try:
        for commit in commits:
            git_ops.checkout_detached(worktree_path, commit)
            result = build_repo(
                repo_state,
                policy,
                workspace_root=worktree_path,
                source="git_bootstrap",
                run_addon_hooks=False,
            )
            if verbose:
                _LOGGER.info(
                    "[bootstrap] %s -> %s (%s)",
                    commit[:12],
                    result.snapshot_id,
                    result.status,
                )
    finally:
        _cleanup_bootstrap_worktree(repo_state.repo_root, worktree_path)


def list_bootstrap_commits(repo_root: Path, commit_limit: int, day_limit: int) -> List[str]:
    return git_ops.list_commits(repo_root, commit_limit, day_limit)


def _prepare_bootstrap_worktree(repo_root: Path, sciona_dir: Path) -> Path:
    worktree_path = sciona_dir / "bootstrap-worktree"
    if worktree_path.exists():
        shutil.rmtree(worktree_path)
    git_ops.worktree_add(repo_root, worktree_path)
    return worktree_path


def _cleanup_bootstrap_worktree(repo_root: Path, worktree_path: Path) -> None:
    try:
        git_ops.worktree_remove(repo_root, worktree_path)
    except git_ops.GitError:
        pass
    if worktree_path.exists():
        sciona_dir = repo_root / ".sciona"
        try:
            resolved = worktree_path.resolve()
            sciona_root = sciona_dir.resolve()
            if resolved.name != "bootstrap-worktree":
                raise ValueError(f"Invalid worktree name: {resolved.name}")
            if sciona_root not in resolved.parents:
                raise ValueError(f"Worktree outside .sciona: {worktree_path}")
        except OSError:
            raise ValueError(f"Failed to resolve worktree path: {worktree_path}") from None
        shutil.rmtree(worktree_path)


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
    "list_bootstrap_commits",
    "run_bootstrap_builds",
    "seed_initial_snapshots",
]
