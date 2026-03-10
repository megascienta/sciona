# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Progress reporting protocols and helpers."""

from __future__ import annotations

from time import perf_counter
import weakref
from typing import Callable, Optional, Protocol

import typer


class ProgressHandle(Protocol):
    def advance(self, steps: int = 1) -> None:
        """Advance the progress indicator by the given step count."""

    def close(self) -> None:
        """Finalize the progress indicator."""


ProgressFactory = Callable[[str, int], Optional[ProgressHandle]]
PhaseReporter = Callable[[str], None]


class _ProgressBarHandle:
    def __init__(self, bar: object, *, on_close: Callable[[], None] | None = None) -> None:
        self.bar = bar
        self._closed = False
        self._on_close = on_close
        self._finalizer = weakref.finalize(self, self._cleanup, bar)

    def advance(self, steps: int = 1) -> None:
        self.bar.update(steps)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.bar.__exit__(None, None, None)
        self._finalizer.detach()
        if self._on_close is not None:
            self._on_close()

    @staticmethod
    def _cleanup(bar: object) -> None:
        try:
            bar.__exit__(None, None, None)
        except Exception:
            pass


def make_progress_handle(label: str, total: int) -> Optional[ProgressHandle]:
    if total <= 0:
        return None
    bar = typer.progressbar(length=total, label=label)
    bar.__enter__()
    return _ProgressBarHandle(bar)


def make_progress_factory() -> ProgressFactory:
    """Return a progress factory that renders CLI progress bars."""

    def factory(label: str, total: int) -> Optional[ProgressHandle]:
        return make_progress_handle(label, total)

    return factory


def emit_progress_phase(label: str) -> None:
    """Emit a visible phase label for uncounted build work."""
    typer.echo(label)


def make_phase_reporter() -> PhaseReporter:
    """Return a reporter for phase-oriented progress messages."""

    def reporter(label: str) -> None:
        emit_progress_phase(label)

    return reporter


class BuildProgress:
    """Shared build-phase reporter for numbered status lines and progress bars."""

    def __init__(self, *, total_steps: int) -> None:
        self.total_steps = total_steps
        self._step = 0
        self._current_key: str | None = None
        self._current_label: str | None = None
        self._current_started_at: float | None = None
        self._phase_timings: dict[str, float] = {}

    _PHASE_KEYS = {
        "Computing build fingerprint": "compute_build_fingerprint",
        "Discovering files": "discover_files",
        "Preparing snapshots": "prepare_snapshots",
        "Registering modules": "register_modules",
        "Analyzing": "analyze",
        "Analyzing artifacts": "analyze_artifacts",
        "Refreshing artifacts": "refresh_artifacts",
        "Writing call artifacts": "write_call_artifacts",
        "Rebuilding graph index": "rebuild_graph_index",
        "Rebuilding graph rollups": "rebuild_graph_rollups",
    }

    def _next_label(self, label: str) -> str:
        self._step += 1
        return f"[{self._step}/{self.total_steps}] {label}"

    def emit_phase(self, label: str) -> None:
        self._complete_active_phase()
        self._current_key = self._phase_key(label)
        self._current_label = label
        self._current_started_at = perf_counter()
        typer.echo(self._next_label(label))

    def phase_timings(self) -> dict[str, float]:
        self._complete_active_phase()
        return dict(self._phase_timings)

    def finalize(self) -> None:
        self._complete_active_phase()

    def _phase_key(self, label: str) -> str:
        return self._PHASE_KEYS.get(label, label.lower().replace(" ", "_"))

    def _record_phase(self, *, key: str, elapsed: float) -> None:
        self._phase_timings[key] = max(elapsed, 0.0)
        typer.echo(f"       {elapsed:.2f}s")

    def _complete_active_phase(self) -> None:
        if (
            self._current_key is None
            or self._current_started_at is None
        ):
            return
        self._record_phase(
            key=self._current_key,
            elapsed=perf_counter() - self._current_started_at,
        )
        self._current_key = None
        self._current_label = None
        self._current_started_at = None

    def make_progress_factory(self) -> ProgressFactory:
        def factory(label: str, total: int) -> Optional[ProgressHandle]:
            self._complete_active_phase()
            phase_key = self._phase_key(label)
            started_at = perf_counter()
            if total <= 0:
                self._record_phase(key=phase_key, elapsed=0.0)
                return None
            bar = typer.progressbar(length=total, label=self._next_label(label))
            bar.__enter__()
            return _ProgressBarHandle(
                bar,
                on_close=lambda: self._record_phase(
                    key=phase_key,
                    elapsed=perf_counter() - started_at,
                ),
            )

        return factory


def make_build_progress(*, total_steps: int) -> BuildProgress:
    """Create a numbered build progress reporter."""

    return BuildProgress(total_steps=total_steps)
