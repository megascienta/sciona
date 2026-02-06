# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""LLM provider boundary."""

from .adapter import Adapter, LLMRequest, LLMResponse

__all__ = ["Adapter", "LLMRequest", "LLMResponse"]
