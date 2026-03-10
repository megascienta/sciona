"""Compatibility alias for extraction language registry interfaces."""

from __future__ import annotations

import sys

from ..interfaces import language_registry as _language_registry

sys.modules[__name__] = _language_registry
