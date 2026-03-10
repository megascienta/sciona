"""Compatibility alias for extraction language adapter interfaces."""

from __future__ import annotations

import sys

from ..interfaces import language_adapter as _language_adapter

sys.modules[__name__] = _language_adapter
