# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.pipelines.progress import make_progress_handle


def test_make_progress_handle_returns_none_for_zero() -> None:
    assert make_progress_handle("noop", 0) is None


def test_make_progress_handle_advances_and_closes() -> None:
    handle = make_progress_handle("work", 1)
    assert handle is not None
    handle.advance(1)
    handle.close()
