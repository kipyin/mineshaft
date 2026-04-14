from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Pos:
    x: int
    y: int

    def offset(self, dx: int, dy: int) -> Pos:
        return Pos(self.x + dx, self.y + dy)
