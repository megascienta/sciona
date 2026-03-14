# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Progress reporting protocols and helpers."""

from __future__ import annotations

from time import perf_counter
import sys
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
    def __init__(
        self,
        *,
        label: str,
        total: int,
        on_close: Callable[[str], None] | None = None,
    ) -> None:
        self.label = label
        self.total = total
        self.current = 0
        self._closed = False
        self._on_close = on_close
        self._finalizer = weakref.finalize(self, self._cleanup)
        self._render()

    def advance(self, steps: int = 1) -> None:
        self.current = min(self.total, self.current + steps)
        self._render()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._finalizer.detach()
        if self._on_close is not None:
            self._on_close(self._completed_line())
        else:
            sys.stdout.write("\n")
            sys.stdout.flush()

    @staticmethod
    def _cleanup() -> None:
        try:
            sys.stdout.write("\n")
            sys.stdout.flush()
        except Exception:
            pass

    def _completed_line(self) -> str:
        width = 36
        bar = "#" * width
        return f"{self.label}  [{bar}]  100%"

    def _render(self) -> None:
        width = 36
        fraction = 0.0 if self.total <= 0 else self.current / self.total
        filled = max(0, min(width, int(round(fraction * width))))
        percentage = f"{int(fraction * 100):3d}%"
        bar = "#" * filled + "." * (width - filled)
        sys.stdout.write(f"\r{self.label}  [{bar}]  {percentage}")
        sys.stdout.flush()


def make_progress_handle(label: str, total: int) -> Optional[ProgressHandle]:
    if total <= 0:
        return None
    return _ProgressBarHandle(label=label, total=total)


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
        "Building structural index": "build_structural_index",
        "Extracting call observations": "derive_call_artifacts",
        "Preparing callsite pairs": "prepare_callsite_pairs",
        "Writing callsite pairs": "write_callsite_pairs",
        "Rebuilding call graph index": "rebuild_graph_index",
        "Rebuilding graph rollups": "rebuild_graph_rollups",
        "Diagnostic classification": "diagnostic_classification",
    }

    def _next_label(self, label: str) -> str:
        self._step += 1
        return f"[{self._step}/{self.total_steps}] {label}"

    def emit_phase(self, label: str) -> None:
        self._complete_active_phase()
        self._current_key = self._phase_key(label)
        self._current_label = label
        self._current_started_at = perf_counter()
        self._next_label(label)

    def phase_timings(self) -> dict[str, float]:
        self._complete_active_phase()
        return dict(self._phase_timings)

    def finalize(self) -> None:
        self._complete_active_phase()

    def _phase_key(self, label: str) -> str:
        return self._PHASE_KEYS.get(label, label.lower().replace(" ", "_"))

    def _record_phase(
        self,
        *,
        key: str,
        elapsed: float,
        line: str | None = None,
    ) -> None:
        self._phase_timings[key] = max(elapsed, 0.0)
        if line is None:
            typer.echo(f"[{self._step}/{self.total_steps}] {self._current_label} - {elapsed:.2f}s")
        else:
            sys.stdout.write(f"\r{line} - {elapsed:.2f}s\n")
            sys.stdout.flush()

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
            return _ProgressBarHandle(
                label=self._next_label(label),
                total=total,
                on_close=lambda line: self._record_phase(
                    key=phase_key,
                    elapsed=perf_counter() - started_at,
                    line=line,
                ),
            )

        return factory


def make_build_progress(*, total_steps: int) -> BuildProgress:
    """Create a numbered build progress reporter."""

    return BuildProgress(total_steps=total_steps)
