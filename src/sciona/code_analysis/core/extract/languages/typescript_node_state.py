# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""State container for TypeScript node extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .lexical_naming import LexicalNameDisambiguator


@dataclass
class TypeScriptNodeState:
    class_stack: List[str] = field(default_factory=list)
    class_span_stack: List[tuple[int, int]] = field(default_factory=list)
    callable_stack: List[str] = field(default_factory=list)
    module_functions: set[str] = field(default_factory=set)
    class_methods: dict[str, set[str]] = field(default_factory=dict)
    class_name_map: dict[str, str] = field(default_factory=dict)
    class_name_candidates: dict[str, set[str]] = field(default_factory=dict)
    instance_map: dict[str, str] = field(default_factory=dict)
    class_instance_map: dict[str, dict[str, str]] = field(default_factory=dict)
    pending_instance_assignments: list[tuple[str, tuple[str, ...]]] = field(
        default_factory=list
    )
    pending_class_instances: list[tuple[str, str, tuple[str, ...]]] = field(
        default_factory=list
    )
    pending_alias_assignments: list[tuple[str, str]] = field(default_factory=list)
    pending_class_aliases: list[tuple[str, str, str]] = field(default_factory=list)
    pending_calls: list[tuple[str, str, object | None, str | None]] = field(
        default_factory=list
    )
    name_disambiguator: LexicalNameDisambiguator = field(
        default_factory=LexicalNameDisambiguator
    )


__all__ = ["TypeScriptNodeState"]
