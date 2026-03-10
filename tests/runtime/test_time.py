# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from datetime import datetime, timezone

from sciona.runtime.common.time import utc_now


def test_utc_now_returns_isoformat() -> None:
    value = utc_now()
    parsed = datetime.fromisoformat(value)
    assert parsed.tzinfo is not None
    assert parsed.tzinfo.utcoffset(parsed) == timezone.utc.utcoffset(parsed)
