# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Build policy resolution."""

from __future__ import annotations

from ..domain.policies import AnalysisPolicy, ArtifactPolicy, BuildPolicy
from ..domain.repository import RepoState


def resolve_build_policy(
    repo_state: RepoState,
    *,
    refresh_artifacts: bool = True,
    refresh_calls: bool = True,
    force_rebuild: bool = False,
) -> BuildPolicy:
    if repo_state.config is None:
        raise ValueError("Build policy requires repository configuration.")
    runtime_cfg = repo_state.config.runtime
    analysis = AnalysisPolicy(
        languages=runtime_cfg.languages,
    )
    artifacts = ArtifactPolicy(
        refresh_artifacts=refresh_artifacts,
        refresh_calls=refresh_calls,
    )
    return BuildPolicy(
        analysis=analysis,
        artifacts=artifacts,
        force_rebuild=force_rebuild,
    )


__all__ = ["resolve_build_policy"]
