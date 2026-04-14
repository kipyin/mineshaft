from __future__ import annotations


def _mortonish(a: int, b: int) -> int:
    x = a & 0xFFFFFFFF
    y = b & 0xFFFFFFFF
    return (x * 73856093) ^ (y * 19349663)


def unit_float(seed: int, x: int, y: int) -> float:
    """Deterministic [0,1) hash."""
    h = _mortonish(x + seed * 1013904223, y + seed * 1664525)
    h ^= h >> 16
    h *= 0x7FFBCEBD
    h ^= h >> 16
    return (h & 0xFFFFFFFF) / 4294967296.0


def fbm2(seed: int, x: int, y: int) -> float:
    """Very small 2-octave value noise in [0,1)."""
    z = 0.0
    z += unit_float(seed ^ 1, x, y)
    z += unit_float(seed ^ 2, x // 2, y // 2) * 0.5
    return z / 1.5
