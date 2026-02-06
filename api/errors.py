"""Public error types (stable)."""

from __future__ import annotations

from ..pipelines.errors import ConfigError
from ..runtime.errors import ScionaError

__all__ = ["ScionaError", "ConfigError"]
