# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Profile query wrappers over the shared extraction query runtime."""

from __future__ import annotations

from ..core.extract.utils import find_nodes_of_types_query


def find_profile_nodes_of_types(
    node,
    *,
    language_name: str,
    node_types: tuple[str, ...],
    capture_name: str = "node",
) -> list[object]:
    return find_nodes_of_types_query(
        node,
        language_name=language_name,
        node_types=node_types,
        capture_name=capture_name,
    )
