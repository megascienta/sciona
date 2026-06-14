# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Reducer overlay support profile."""

from __future__ import annotations


OVERLAY_PROFILE: dict[str, dict[str, object]] = {
    "snapshot_provenance": {
        "overlay_supported": True,
        "scope_type": "unknown",
        "affected_by": [],
    },
    "structural_index": {
        "overlay_supported": True,
        "scope_type": "codebase",
        "affected_by": ["nodes", "edges"],
    },
    "module_overview": {
        "overlay_supported": True,
        "scope_type": "module",
        "affected_by": ["nodes", "edges"],
    },
    "callable_overview": {
        "overlay_supported": True,
        "scope_type": "callable",
        "affected_by": ["nodes"],
    },
    "classifier_overview": {
        "overlay_supported": True,
        "scope_type": "classifier",
        "affected_by": ["nodes"],
    },
    "file_outline": {
        "overlay_supported": True,
        "scope_type": "file",
        "affected_by": ["nodes"],
    },
    "dependency_edges": {
        "overlay_supported": True,
        "scope_type": "module",
        "affected_by": ["edges"],
    },
    "symbol_lookup": {
        "overlay_supported": True,
        "scope_type": "query",
        "affected_by": ["nodes"],
    },
    "symbol_references": {
        "overlay_supported": True,
        "scope_type": "query",
        "affected_by": ["nodes"],
    },
    "classifier_call_graph_summary": {
        "overlay_supported": True,
        "scope_type": "classifier",
        "affected_by": ["calls"],
    },
    "module_call_graph_summary": {
        "overlay_supported": True,
        "scope_type": "module",
        "affected_by": ["calls"],
    },
    "fan_summary": {
        "overlay_supported": True,
        "scope_type": "fan",
        "affected_by": ["calls", "edges"],
    },
    "hotspot_summary": {
        "overlay_supported": True,
        "scope_type": "codebase",
        "affected_by": ["nodes", "edges"],
    },
    "classifier_inheritance": {
        "overlay_supported": True,
        "scope_type": "classifier",
        "affected_by": [],
    },
    "callable_source": {
        "overlay_supported": True,
        "scope_type": "callable",
        "affected_by": [],
    },
    "concatenated_source": {
        "overlay_supported": True,
        "scope_type": "unknown",
        "affected_by": [],
    },
}


__all__ = ["OVERLAY_PROFILE"]
