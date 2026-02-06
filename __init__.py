"""SCIONA package entrypoint."""

from __future__ import annotations

import pkgutil

from .runtime import constants
from .runtime import identity
from . import api

__path__ = pkgutil.extend_path(__path__, __name__)  # type: ignore[name-defined]

TOOL_VERSION = constants.TOOL_VERSION

__all__ = ["TOOL_VERSION", "api", "constants", "identity"]
__version__ = TOOL_VERSION
