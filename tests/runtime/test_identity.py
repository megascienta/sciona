# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.runtime.identity import instance_id, structural_id


def test_structural_id_is_deterministic() -> None:
    first = structural_id("module", "python", "pkg.alpha")
    second = structural_id("module", "python", "pkg.alpha")
    other = structural_id("module", "python", "pkg.beta")
    assert first == second
    assert first != other
    assert len(first) == 40


def test_instance_id_prefixes_snapshot() -> None:
    assert instance_id("snap", "abc") == "snap:abc"
