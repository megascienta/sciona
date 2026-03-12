# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Reducer overlay support profile."""

from __future__ import annotations


OVERLAY_PROFILE: dict[str, dict[str, object]] = {
    "snapshot_provenance": {
        "supports_patch": False,
        "scope_type": "unknown",
        "affected_by": [],
    },
    "structural_index": {
        "supports_patch": True,
        "scope_type": "codebase",
        "affected_by": ["nodes", "edges"],
    },
    "module_overview": {
        "supports_patch": True,
        "scope_type": "module",
        "affected_by": ["nodes", "edges"],
    },
    "callable_overview": {
        "supports_patch": True,
        "scope_type": "callable",
        "affected_by": ["nodes"],
    },
    "classifier_overview": {
        "supports_patch": True,
        "scope_type": "classifier",
        "affected_by": ["nodes"],
    },
    "file_outline": {
        "supports_patch": True,
        "scope_type": "file",
        "affected_by": ["nodes"],
    },
    "dependency_edges": {
        "supports_patch": True,
        "scope_type": "module",
        "affected_by": ["edges"],
    },
    "symbol_lookup": {
        "supports_patch": True,
        "scope_type": "query",
        "affected_by": ["nodes"],
    },
    "symbol_references": {
        "supports_patch": True,
        "scope_type": "query",
        "affected_by": ["nodes"],
    },
    "callsite_pairs_index": {
        "supports_patch": True,
        "scope_type": "callable",
        "affected_by": ["calls"],
    },
    "classifier_call_graph_summary": {
        "supports_patch": True,
        "scope_type": "classifier",
        "affected_by": ["calls"],
    },
    "module_call_graph_summary": {
        "supports_patch": True,
        "scope_type": "module",
        "affected_by": ["calls"],
    },
    "call_resolution_quality": {
        "supports_patch": True,
        "scope_type": "metrics",
        "affected_by": ["calls"],
    },
    "call_resolution_drop_summary": {
        "supports_patch": True,
        "scope_type": "metrics",
        "affected_by": ["calls"],
    },
    "fan_summary": {
        "supports_patch": True,
        "scope_type": "fan",
        "affected_by": ["calls", "edges"],
    },
    "hotspot_summary": {
        "supports_patch": True,
        "scope_type": "codebase",
        "affected_by": ["nodes", "edges"],
    },
    "classifier_inheritance": {
        "supports_patch": False,
        "scope_type": "classifier",
        "affected_by": [],
    },
    "callable_source": {
        "supports_patch": False,
        "scope_type": "callable",
        "affected_by": [],
    },
    "concatenated_source": {
        "supports_patch": False,
        "scope_type": "unknown",
        "affected_by": [],
    },
}


__all__ = ["OVERLAY_PROFILE"]
