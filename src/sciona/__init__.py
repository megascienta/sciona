# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""SCIONA package entrypoint."""

from __future__ import annotations

import pkgutil

from . import api
from .runtime import constants
from .runtime import identity
from .version import TOOL_VERSION, __version__

__path__ = pkgutil.extend_path(__path__, __name__)  # type: ignore[name-defined]

__all__ = ["TOOL_VERSION", "__version__", "api", "constants", "identity"]
