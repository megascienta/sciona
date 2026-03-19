# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared normalized import model across language extractors."""

from __future__ import annotations

from dataclasses import dataclass, field

from .local_binding_ir import LocalBindingFact, validated_local_binding_fact


@dataclass
class NormalizedImportModel:
    modules: list[str] = field(default_factory=list)
    import_aliases: dict[str, str] = field(default_factory=dict)
    member_aliases: dict[str, str] = field(default_factory=dict)
    local_binding_facts: list[LocalBindingFact] = field(default_factory=list)
    raw_module_map: dict[str, str] = field(default_factory=dict)
    static_wildcard_targets: set[str] = field(default_factory=set)
    imports_seen: int = 0
    imports_internal: int = 0
    imports_filtered_not_internal: int = 0

    def add_local_binding_fact(
        self,
        symbol: str,
        target: str,
        *,
        binding_kind: str,
        evidence_kind: str,
        language: str,
    ) -> None:
        self.local_binding_facts.append(
            validated_local_binding_fact(
                symbol,
                target,
                binding_kind=binding_kind,
                evidence_kind=evidence_kind,
                language=language,
            )
        )
