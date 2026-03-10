# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.data_storage.common.encoding import bool_to_int


def test_bool_to_int() -> None:
    assert bool_to_int(True) == 1
    assert bool_to_int(False) == 0
