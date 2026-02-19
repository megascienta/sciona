# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.runtime.rollback import RollbackPolicy


def test_rollback_policy_values() -> None:
    assert RollbackPolicy.NONE.value == "none"
    assert RollbackPolicy.CORE_ONLY.value == "core_only"
    assert RollbackPolicy.PAIR_REQUIRED.value == "pair_required"
