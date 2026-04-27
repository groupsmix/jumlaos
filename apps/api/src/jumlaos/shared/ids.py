"""Stable ID generators (UUIDv7-ish)."""

from __future__ import annotations

import os
import time
import uuid


def new_uuid() -> uuid.UUID:
    """Generate a time-ordered UUID (v7-like)."""
    ts_ms = int(time.time() * 1000)
    rand = os.urandom(10)
    # 48 bits of timestamp + 4-bit version (7) + 12-bit rand_a + 2-bit variant + 62 bits rand_b
    time_bytes = ts_ms.to_bytes(6, "big")
    rand_a = rand[:2]
    rand_b = rand[2:]
    # version nibble
    b6 = (0x70 | (rand_a[0] & 0x0F)).to_bytes(1, "big")
    # variant nibble (10xx)
    b8 = (0x80 | (rand_b[0] & 0x3F)).to_bytes(1, "big")
    raw = time_bytes + b6 + rand_a[1:2] + b8 + rand_b[1:]
    return uuid.UUID(bytes=raw[:16])


def new_hex() -> str:
    return new_uuid().hex
