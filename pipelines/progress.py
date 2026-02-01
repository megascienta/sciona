"""Progress reporting protocols and helpers."""
from __future__ import annotations

import weakref
from typing import Callable, Optional, Protocol

import typer


class ProgressHandle(Protocol):
    def advance(self, steps: int = 1) -> None:
        """Advance the progress indicator by the given step count."""

    def close(self) -> None:
        """Finalize the progress indicator."""


ProgressFactory = Callable[[str, int], Optional[ProgressHandle]]


class _ProgressBarHandle:
    def __init__(self, bar: object) -> None:
        self.bar = bar
        self._closed = False
        self._finalizer = weakref.finalize(self, self._cleanup, bar)

    def advance(self, steps: int = 1) -> None:
        self.bar.update(steps)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.bar.__exit__(None, None, None)
        self._finalizer.detach()

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
