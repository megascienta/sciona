# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.pipelines.progress import (
    build_progress_total_steps,
    make_build_progress,
    make_progress_handle,
)


def test_make_progress_handle_returns_none_for_zero() -> None:
    assert make_progress_handle("noop", 0) is None


def test_make_progress_handle_advances_and_closes() -> None:
    handle = make_progress_handle("work", 1)
    assert handle is not None
    handle.advance(1)
    handle.close()


def test_build_progress_numbers_phases_and_progress_labels() -> None:
    progress = make_build_progress(total_steps=10)

    assert progress._next_label("Phase one") == "[1/10] Phase one"
    assert progress._next_label("Phase two") == "[2/10] Phase two"
    assert progress._next_label("Phase three") == "[3/10] Phase three"


def test_build_progress_total_steps_matches_phase_definitions() -> None:
    assert build_progress_total_steps(diagnostic=True) == len(
        make_build_progress(total_steps=1)._PHASE_KEYS
    )
    assert (
        build_progress_total_steps(diagnostic=False)
        == build_progress_total_steps(diagnostic=True) - 1
    )
