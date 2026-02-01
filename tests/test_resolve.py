from sciona.data_storage.connections import core
from sciona.pipelines import resolve as resolver
from sciona.pipelines.config import public as config
from sciona.pipelines.policy import prompt as prompt_policy

from tests.helpers import seed_repo_with_snapshot


def test_resolve_callable_by_qualified_name(tmp_path):
    repo_root, _ = seed_repo_with_snapshot(tmp_path)
    db_path = config.get_db_path(repo_root)
    with core(db_path, repo_root=repo_root) as conn:
        snapshot_id = prompt_policy.resolve_latest_snapshot(conn)
        result = resolver.identifier(
            conn,
            snapshot_id,
            kind="callable",
            identifier="pkg.alpha.service.helper",
        )

    assert result.status == "exact"
    assert result.resolved_id == "func_alpha"


def test_resolve_callable_best_fits(tmp_path):
    repo_root, _ = seed_repo_with_snapshot(tmp_path)
    db_path = config.get_db_path(repo_root)
    with core(db_path, repo_root=repo_root) as conn:
        snapshot_id = prompt_policy.resolve_latest_snapshot(conn)
        result = resolver.identifier(
            conn,
            snapshot_id,
            kind="callable",
            identifier="service",
        )

    assert result.status == "missing"
    assert any(
        candidate.qualified_name == "pkg.alpha.service.helper"
        for candidate in result.candidates
    )
