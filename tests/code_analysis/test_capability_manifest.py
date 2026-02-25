# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import json
from pathlib import Path

from sciona.code_analysis.core.extract.languages.capability_manifest import (
    build_capability_manifest,
)


def test_capability_manifest_is_current() -> None:
    manifest_path = Path("docs/CAPABILITY_MANIFEST.json")
    on_disk = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert on_disk == build_capability_manifest()

