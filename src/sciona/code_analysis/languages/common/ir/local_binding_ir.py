# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared local-binding intermediate representation."""

from __future__ import annotations

from dataclasses import dataclass

from ..contracts.loader import load_contract_json


_LOCAL_BINDING_CONTRACT = load_contract_json("local_binding_resolution.json")

ALLOWED_BINDING_PRECEDENCE = tuple(
    str(value) for value in _LOCAL_BINDING_CONTRACT["binding_precedence"]
)
ALLOWED_BINDING_KINDS = frozenset(
    str(value) for value in _LOCAL_BINDING_CONTRACT["allowed_binding_kinds"]
)
ALLOWED_BINDING_EVIDENCE = frozenset(
    str(value) for value in _LOCAL_BINDING_CONTRACT["allowed_binding_evidence"]
)
FORBIDDEN_DYNAMIC_SHAPES = frozenset(
    str(value) for value in _LOCAL_BINDING_CONTRACT["forbidden_dynamic_shapes"]
)


@dataclass(frozen=True)
class LocalBindingFact:
    symbol: str
    target: str
    binding_kind: str
    evidence_kind: str
    language: str

    def validate(self) -> None:
        if not self.symbol:
            raise ValueError("local binding fact requires non-empty symbol")
        if not self.target:
            raise ValueError("local binding fact requires non-empty target")
        if self.binding_kind not in ALLOWED_BINDING_KINDS:
            raise ValueError(f"unsupported binding kind: {self.binding_kind}")
        if self.evidence_kind not in ALLOWED_BINDING_EVIDENCE:
            raise ValueError(f"unsupported evidence kind: {self.evidence_kind}")
        if not self.language:
            raise ValueError("local binding fact requires non-empty language")


def validated_local_binding_fact(
    symbol: str,
    target: str,
    *,
    binding_kind: str,
    evidence_kind: str,
    language: str,
) -> LocalBindingFact:
    fact = LocalBindingFact(
        symbol=symbol,
        target=target,
        binding_kind=binding_kind,
        evidence_kind=evidence_kind,
        language=language,
    )
    fact.validate()
    return fact


def alias_maps_from_binding_facts(
    facts: list[LocalBindingFact],
) -> tuple[dict[str, str], dict[str, str]]:
    import_aliases: dict[str, str] = {}
    member_aliases: dict[str, str] = {}
    for fact in facts:
        if fact.binding_kind in {
            "module_alias",
            "namespace_alias",
            "constructor_or_classifier_import",
        }:
            import_aliases.setdefault(fact.symbol, fact.target)
        elif fact.binding_kind in {
            "direct_import_symbol",
            "destructured_static_member",
            "static_member_receiver",
            "static_export_surface",
            "static_import_member",
        }:
            member_aliases.setdefault(fact.symbol, fact.target)
    return import_aliases, member_aliases


__all__ = [
    "ALLOWED_BINDING_EVIDENCE",
    "ALLOWED_BINDING_KINDS",
    "ALLOWED_BINDING_PRECEDENCE",
    "FORBIDDEN_DYNAMIC_SHAPES",
    "LocalBindingFact",
    "alias_maps_from_binding_facts",
    "validated_local_binding_fact",
]
