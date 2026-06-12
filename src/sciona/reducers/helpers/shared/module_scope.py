# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared CoreDB-backed module scope resolution for reducers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


ScopeKind = Literal["module", "package_prefix"]


@dataclass(frozen=True)
class ModuleScope:
    scope_filter: str
    scope_kind: ScopeKind
    module_ids: list[str]
    root: dict[str, Any] | None = None

    @property
    def module_qualified_name(self) -> str:
        if self.root and self.root.get("qualified_name"):
            return str(self.root["qualified_name"])
        return self.scope_filter


def resolve_module_scope(
    conn,
    snapshot_id: str,
    selector: str,
    *,
    reducer_name: str,
    allow_package_prefix: bool = True,
    include_descendants_for_exact: bool = True,
) -> ModuleScope:
    normalized = str(selector).strip()
    if not normalized:
        raise ValueError(f"{reducer_name} module selector must be non-empty.")

    root = _lookup_exact_module(conn, snapshot_id, normalized)
    if root:
        if allow_package_prefix and include_descendants_for_exact:
            module_ids = _module_ids_for_prefix(
                conn, snapshot_id, str(root["qualified_name"])
            )
        else:
            module_ids = [str(root["structural_id"])]
        return ModuleScope(
            scope_filter=normalized,
            scope_kind="module",
            module_ids=module_ids,
            root=root,
        )

    if allow_package_prefix:
        module_ids = _module_ids_for_prefix(conn, snapshot_id, normalized)
        if module_ids:
            return ModuleScope(
                scope_filter=normalized,
                scope_kind="package_prefix",
                module_ids=module_ids,
                root=None,
            )

    raise ValueError(
        f"{reducer_name} module '{normalized}' not found in snapshot '{snapshot_id}'."
    )


def _lookup_exact_module(conn, snapshot_id: str, selector: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT
            sn.structural_id,
            sn.node_type,
            sn.language,
            ni.qualified_name,
            ni.file_path,
            ni.start_line,
            ni.end_line,
            ni.start_byte,
            ni.end_byte,
            ni.content_hash
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type = 'module'
          AND (sn.structural_id = ? OR ni.qualified_name = ?)
        LIMIT 1
        """,
        (snapshot_id, selector, selector),
    ).fetchone()
    return dict(row) if row else None


def _module_ids_for_prefix(conn, snapshot_id: str, prefix: str) -> list[str]:
    rows = conn.execute(
        """
        SELECT sn.structural_id
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type = 'module'
          AND (ni.qualified_name = ? OR ni.qualified_name LIKE ?)
        ORDER BY ni.qualified_name
        """,
        (snapshot_id, prefix, f"{prefix}.%"),
    ).fetchall()
    return [str(row["structural_id"]) for row in rows]


__all__ = ["ModuleScope", "resolve_module_scope"]
