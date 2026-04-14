from __future__ import annotations

from enum import Enum


class Direction(Enum):
    N = (0, -1)
    S = (0, 1)
    W = (-1, 0)
    E = (1, 0)

    @property
    def dx(self) -> int:
        return self.value[0]

    @property
    def dy(self) -> int:
        return self.value[1]
