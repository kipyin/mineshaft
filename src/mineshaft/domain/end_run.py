from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EndRun:
    """End dimension: single dragon encounter (no block grid)."""

    dragon_hp: int
    dragon_max_hp: int
    # Alternates dragon attack pattern (ground vs breath); see resolve_end_dragon_exchange.
    phase: int = 0
