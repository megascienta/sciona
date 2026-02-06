# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.pipelines import resolve as resolver

from tests.helpers import seed_repo_with_snapshot


def test_resolve_callable_by_qualified_name(tmp_path):
    repo_root, _ = seed_repo_with_snapshot(tmp_path)
    result = resolver.identifier_for_repo(
        kind="callable",
        identifier="pkg.alpha.service.helper",
        repo_root=repo_root,
    )

    assert result.status == "exact"
    assert result.resolved_id == "func_alpha"


def test_resolve_callable_best_fits(tmp_path):
    repo_root, _ = seed_repo_with_snapshot(tmp_path)
    result = resolver.identifier_for_repo(
        kind="callable",
        identifier="service",
        repo_root=repo_root,
    )

    assert result.status == "missing"
    assert any(
        candidate.qualified_name == "pkg.alpha.service.helper"
        for candidate in result.candidates
    )
