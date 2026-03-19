# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from sciona.code_analysis.languages.common.support.capability_manifest import (
    build_capability_manifest,
)


def test_walker_capabilities_declare_query_access_mode() -> None:
    manifest = build_capability_manifest()
    for entries in manifest["walker_capabilities"].values():
        for entry in entries:
            query_access = entry.get("query_access")
            assert isinstance(query_access, dict)
            assert query_access.get("mode") in {"direct", "nested"}


def test_walker_capabilities_align_with_declared_query_surfaces() -> None:
    manifest = build_capability_manifest()
    queries = manifest["queries"]

    for language, entries in manifest["walker_capabilities"].items():
        direct_surface = set(queries[language]["structural_nodes"])
        carrier_surface = set(queries[language].get("structural_carriers", []))
        declared_surface = direct_surface | carrier_surface

        for entry in entries:
            node_types = set(entry["node_types"])
            query_access = entry["query_access"]
            if query_access["mode"] == "direct":
                assert node_types <= direct_surface, (
                    f"{language}:{entry['construct']} references node types outside "
                    "the direct structural query surface"
                )
                continue

            anchors = set(query_access.get("anchors") or [])
            assert anchors, f"{language}:{entry['construct']} must declare nested anchors"
            assert anchors <= declared_surface, (
                f"{language}:{entry['construct']} declares nested anchors outside "
                "the language query surface"
            )
            assert not node_types <= direct_surface, (
                f"{language}:{entry['construct']} should use direct query access "
                "instead of nested"
            )
