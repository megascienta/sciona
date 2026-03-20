# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.code_analysis.languages.common.capabilities.walker_capabilities import (
    build_walker_capabilities,
)
from sciona.code_analysis.config import LANGUAGE_CONFIG


def test_walker_capabilities_cover_supported_languages() -> None:
    capabilities = build_walker_capabilities()
    assert set(capabilities) == set(LANGUAGE_CONFIG)


def test_walker_capability_entries_have_structural_mapping_shape() -> None:
    capabilities = build_walker_capabilities()
    for entries in capabilities.values():
        assert entries
        for entry in entries:
            assert set(entry).issuperset(
                {
                "construct",
                "node_types",
                "emits_nodes",
                "emits_edges",
                }
            )
            assert isinstance(entry["construct"], str) and entry["construct"]
            assert isinstance(entry["node_types"], list)
            assert isinstance(entry["emits_nodes"], list)
            assert isinstance(entry["emits_edges"], list)
            if "constraints" in entry:
                assert isinstance(entry["constraints"], list)
