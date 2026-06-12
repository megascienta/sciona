# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.pipelines.ops import resolve as resolver
from sciona.runtime import paths as runtime_paths

from tests.helpers import core_conn, seed_repo_with_snapshot


def test_resolve_callable_by_qualified_name(tmp_path):
    repo_root, _ = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    result = resolver.identifier_for_repo(
        kind="callable",
        identifier=f"{prefix}.pkg.alpha.service.helper",
        repo_root=repo_root,
    )

    assert result.status == "exact"
    assert result.resolved_id == "func_alpha"


def test_resolve_callable_best_fits(tmp_path):
    repo_root, _ = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    result = resolver.identifier_for_repo(
        kind="callable",
        identifier="service",
        repo_root=repo_root,
    )

    assert result.status == "ambiguous"
    assert result.resolved_id is None
    assert any(
        candidate.qualified_name == f"{prefix}.pkg.alpha.service.helper"
        for candidate in result.candidates
    )


def test_resolve_auto_resolves_single_suffix_candidate(tmp_path):
    repo_root, _ = seed_repo_with_snapshot(tmp_path)
    result = resolver.identifier_for_repo(
        kind="callable",
        identifier="helper",
        repo_root=repo_root,
    )

    assert result.status == "resolved"
    assert result.resolved_id == "func_alpha"
    assert result.resolved_from == "helper"


def test_resolve_without_kind_searches_all_kinds(tmp_path):
    repo_root, _ = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    cases = [
        (f"{prefix}.pkg.alpha.service.helper", "func_alpha"),
        (f"{prefix}.pkg.alpha.Service", "cls_alpha"),
        (f"{prefix}.pkg.alpha", "mod_alpha"),
        ("cls_alpha", "cls_alpha"),
    ]
    for identifier, structural_id in cases:
        result = resolver.identifier_for_repo(
            kind=None,
            identifier=identifier,
            repo_root=repo_root,
        )
        assert result.status == "exact", (identifier, result.status)
        assert result.resolved_id == structural_id

    fuzzy = resolver.identifier_for_repo(
        kind=None,
        identifier="Service",
        repo_root=repo_root,
    )
    assert fuzzy.status == "resolved"
    assert fuzzy.resolved_id == "cls_alpha"
    assert fuzzy.resolved_from == "Service"


def test_resolve_missing_only_when_no_candidates(tmp_path):
    repo_root, _ = seed_repo_with_snapshot(tmp_path)
    result = resolver.identifier_for_repo(
        kind="callable",
        identifier="nonexistent_zzz",
        repo_root=repo_root,
    )

    assert result.status == "missing"
    assert result.candidates == tuple()


def test_resolve_multiple_cleared_candidates_stay_ambiguous(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    conn = core_conn(repo_root)
    conn.execute(
        """
        INSERT INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
        VALUES (?, ?, ?, ?)
        """,
        ("func_beta_helper", "callable", "python", snapshot_id),
    )
    conn.execute(
        """
        INSERT INTO node_instances(
            instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"{snapshot_id}:func_beta_helper",
            "func_beta_helper",
            snapshot_id,
            f"{prefix}.pkg.beta.helper",
            "pkg/beta/helper.py",
            1,
            10,
            "hash-func_beta_helper",
        ),
    )
    conn.commit()
    conn.close()

    result = resolver.identifier_for_repo(
        kind="callable",
        identifier="helper",
        repo_root=repo_root,
    )

    assert result.status == "ambiguous"
    assert result.resolved_id is None
    assert len(result.candidates) >= 2


def test_require_identifier_auto_resolves(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = core_conn(repo_root)
    try:
        resolved_id = resolver.require_identifier(
            conn,
            snapshot_id,
            kind="callable",
            identifier="helper",
        )
    finally:
        conn.close()

    assert resolved_id == "func_alpha"


def test_resolve_round_trips_all_printed_forms(tmp_path):
    repo_root, _ = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    cases = [
        ("callable", f"{prefix}.pkg.alpha.service.helper", "func_alpha"),
        ("classifier", f"{prefix}.pkg.alpha.Service", "cls_alpha"),
        ("module", f"{prefix}.pkg.alpha", "mod_alpha"),
    ]
    for kind, qualified_name, structural_id in cases:
        for form in (f"python:{qualified_name}", qualified_name, structural_id):
            result = resolver.identifier_for_repo(
                kind=kind,
                identifier=form,
                repo_root=repo_root,
            )
            assert result.status == "exact", (kind, form, result.status)
            assert result.resolved_id == structural_id


def test_resolve_unknown_language_prefix_is_not_stripped(tmp_path):
    repo_root, _ = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    result = resolver.identifier_for_repo(
        kind="callable",
        identifier=f"rust:{prefix}.pkg.alpha.service.helper",
        repo_root=repo_root,
    )

    assert result.status == "missing"
    assert result.resolved_id is None


def test_resolve_bare_language_prefix_is_missing(tmp_path):
    repo_root, _ = seed_repo_with_snapshot(tmp_path)
    result = resolver.identifier_for_repo(
        kind="callable",
        identifier="python:",
        repo_root=repo_root,
    )

    assert result.status == "missing"
    assert result.candidates == tuple()


def test_resolve_language_prefix_disambiguates_cross_language(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    qualified_name = f"{prefix}.pkg.alpha.service.helper"
    conn = core_conn(repo_root)
    conn.execute(
        """
        INSERT INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
        VALUES (?, ?, ?, ?)
        """,
        ("func_alpha_ts", "callable", "typescript", snapshot_id),
    )
    conn.execute(
        """
        INSERT INTO node_instances(
            instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"{snapshot_id}:func_alpha_ts",
            "func_alpha_ts",
            snapshot_id,
            qualified_name,
            "pkg/alpha/service.ts",
            1,
            10,
            "hash-func_alpha_ts",
        ),
    )
    conn.commit()
    conn.close()

    bare = resolver.identifier_for_repo(
        kind="callable",
        identifier=qualified_name,
        repo_root=repo_root,
    )
    assert bare.status == "ambiguous"

    for language, expected in (("python", "func_alpha"), ("typescript", "func_alpha_ts")):
        result = resolver.identifier_for_repo(
            kind="callable",
            identifier=f"{language}:{qualified_name}",
            repo_root=repo_root,
        )
        assert result.status == "exact", (language, result.status)
        assert result.resolved_id == expected

    fuzzy_bare = resolver.identifier_for_repo(
        kind="callable",
        identifier="helper",
        repo_root=repo_root,
    )
    assert fuzzy_bare.status == "ambiguous"

    fuzzy_prefixed = resolver.identifier_for_repo(
        kind="callable",
        identifier="python:helper",
        repo_root=repo_root,
    )
    assert fuzzy_prefixed.status == "resolved"
    assert fuzzy_prefixed.resolved_id == "func_alpha"
    assert fuzzy_prefixed.resolved_from == "python:helper"
