"""Low-level unit tests for helpers that don't need the mock panel."""

from __future__ import annotations

import pytest
from xui_client.client import _BYTES_PER_GB, _bytes_to_gb


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, 0),
        (-1, 0),
        (1, 1),  # any positive byte count rounds up to at least 1 GiB
        (_BYTES_PER_GB, 1),
        (_BYTES_PER_GB + 1, 2),
        (2 * _BYTES_PER_GB, 2),
        (10 * _BYTES_PER_GB, 10),
        (10 * _BYTES_PER_GB - 1, 10),
    ],
)
def test_bytes_to_gb(value: int, expected: int) -> None:
    assert _bytes_to_gb(value) == expected
