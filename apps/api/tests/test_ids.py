"""F29: UUIDv7 tests — time-ordered, unique, correct version nibble."""

from __future__ import annotations

import time

from jumlaos.shared.ids import new_hex, new_uuid


class TestUUIDv7:
    def test_version_nibble_is_7(self) -> None:
        u = new_uuid()
        assert u.version == 7

    def test_time_ordered(self) -> None:
        a = new_uuid()
        time.sleep(0.002)
        b = new_uuid()
        # UUIDv7 sorts chronologically when compared as bytes.
        assert a.bytes < b.bytes

    def test_unique(self) -> None:
        ids = {new_hex() for _ in range(1000)}
        assert len(ids) == 1000

    def test_hex_length(self) -> None:
        h = new_hex()
        assert len(h) == 32
        int(h, 16)  # must not raise
