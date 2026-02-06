"""CoreDB error types."""

from __future__ import annotations


class SnapshotValidationError(ValueError):
    """Raised when snapshot preconditions for read operations fail."""


class SnapshotNotFoundError(SnapshotValidationError):
    """Raised when snapshot id is unknown."""


class UncommittedSnapshotError(SnapshotValidationError):
    """Raised when committed snapshot is required but id is uncommitted."""
