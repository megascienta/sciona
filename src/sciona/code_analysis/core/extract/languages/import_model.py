# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared normalized import model across language extractors."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NormalizedImportModel:
    modules: list[str] = field(default_factory=list)
    import_aliases: dict[str, str] = field(default_factory=dict)
    member_aliases: dict[str, str] = field(default_factory=dict)
    raw_module_map: dict[str, str] = field(default_factory=dict)
    static_wildcard_targets: set[str] = field(default_factory=set)
    imports_seen: int = 0

