"""Build policy resolution."""
from __future__ import annotations

from ...runtime.policies import AnalysisPolicy, ArtifactPolicy, BuildPolicy
from ...runtime.repo_state import RepoState


def resolve_build_policy(
    repo_state: RepoState,
    *,
    refresh_artifacts: bool = True,
    refresh_calls: bool = True,
) -> BuildPolicy:
    if repo_state.config is None:
        raise ValueError("Build policy requires repository configuration.")
    runtime_cfg = repo_state.config.runtime
    analysis = AnalysisPolicy(
        languages=runtime_cfg.languages,
        snapshot_policy=runtime_cfg.snapshot_policy,
        bootstrap_policy=runtime_cfg.bootstrap_policy,
    )
    artifacts = ArtifactPolicy(
        refresh_artifacts=refresh_artifacts,
        refresh_calls=refresh_calls,
    )
    return BuildPolicy(analysis=analysis, artifacts=artifacts)


__all__ = ["resolve_build_policy"]
