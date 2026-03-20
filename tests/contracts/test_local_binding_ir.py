# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import pytest

from sciona.code_analysis.languages.common.ir import (
    ALLOWED_BINDING_EVIDENCE,
    ALLOWED_BINDING_KINDS,
    ALLOWED_BINDING_PRECEDENCE,
    FORBIDDEN_DYNAMIC_SHAPES,
    LocalBindingFact,
    alias_maps_from_binding_facts,
    binding_candidate_qnames_for_identifier,
    binding_match_for_identifier,
    validated_local_binding_fact,
)


def test_local_binding_contract_surface_is_loaded() -> None:
    assert ALLOWED_BINDING_PRECEDENCE == (
        "shared_tree_sitter_binding_facts",
        "per_language_deepening",
        "minimal_custom_extension",
    )
    assert "direct_import_symbol" in ALLOWED_BINDING_KINDS
    assert "syntax_local_import" in ALLOWED_BINDING_EVIDENCE
    assert "dynamic_import" in FORBIDDEN_DYNAMIC_SHAPES


def test_validated_local_binding_fact_accepts_contract_compliant_fact() -> None:
    fact = validated_local_binding_fact(
        "Matrix",
        "sympy.matrices.dense.Matrix",
        binding_kind="direct_import_symbol",
        evidence_kind="syntax_local_import",
        language="python",
    )
    assert fact == LocalBindingFact(
        symbol="Matrix",
        target="sympy.matrices.dense.Matrix",
        binding_kind="direct_import_symbol",
        evidence_kind="syntax_local_import",
        language="python",
    )


def test_alias_maps_from_binding_facts_splits_import_and_member_bindings() -> None:
    import_aliases, member_aliases = alias_maps_from_binding_facts(
        [
            LocalBindingFact(
                symbol="ns",
                target="repo.src.dep",
                binding_kind="namespace_alias",
                evidence_kind="syntax_local_namespace",
                language="javascript",
            ),
            LocalBindingFact(
                symbol="Widget",
                target="repo.pkg.models.Widget",
                binding_kind="direct_import_symbol",
                evidence_kind="syntax_local_import",
                language="python",
            ),
        ]
    )
    assert import_aliases == {"ns": "repo.src.dep"}
    assert member_aliases == {"Widget": "repo.pkg.models.Widget"}


def test_binding_match_for_identifier_prefers_qualified_head_symbol() -> None:
    match = binding_match_for_identifier(
        "translator.translateKeys",
        [
            LocalBindingFact(
                symbol="translator",
                target="repo.public.src.translator",
                binding_kind="module_alias",
                evidence_kind="syntax_local_import",
                language="javascript",
            ),
            LocalBindingFact(
                symbol="translateKeys",
                target="repo.public.src.translator.translateKeys",
                binding_kind="direct_import_symbol",
                evidence_kind="syntax_local_import",
                language="javascript",
            ),
        ],
    )

    assert match is not None
    assert match.symbol == "translator"
    assert match.binding_kind == "module_alias"


def test_binding_match_for_identifier_falls_back_to_terminal_symbol() -> None:
    match = binding_match_for_identifier(
        "Matrix",
        [
            LocalBindingFact(
                symbol="Matrix",
                target="sympy.matrices.dense.Matrix",
                binding_kind="direct_import_symbol",
                evidence_kind="syntax_local_import",
                language="python",
            )
        ],
    )

    assert match is not None
    assert match.target == "sympy.matrices.dense.Matrix"


def test_binding_candidate_qnames_for_identifier_handles_module_alias_member_calls() -> None:
    candidates = binding_candidate_qnames_for_identifier(
        "translator.translateKeys",
        [
            LocalBindingFact(
                symbol="translator",
                target="repo.public.src.translator",
                binding_kind="module_alias",
                evidence_kind="syntax_local_import",
                language="javascript",
            )
        ],
    )

    assert candidates == ("repo.public.src.translator.translateKeys",)


def test_binding_candidate_qnames_for_identifier_handles_direct_import_symbols() -> None:
    candidates = binding_candidate_qnames_for_identifier(
        "Matrix",
        [
            LocalBindingFact(
                symbol="Matrix",
                target="sympy.matrices.dense.Matrix",
                binding_kind="direct_import_symbol",
                evidence_kind="syntax_local_import",
                language="python",
            )
        ],
    )

    assert candidates == ("sympy.matrices.dense.Matrix",)


@pytest.mark.parametrize(
    ("binding_kind", "evidence_kind", "message"),
    [
        ("dynamic_import", "syntax_local_import", "unsupported binding kind"),
        ("direct_import_symbol", "computed_member_access", "unsupported evidence kind"),
    ],
)
def test_local_binding_fact_rejects_out_of_contract_values(
    binding_kind: str,
    evidence_kind: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        validated_local_binding_fact(
            "symbol",
            "target",
            binding_kind=binding_kind,
            evidence_kind=evidence_kind,
            language="javascript",
        )
