from __future__ import annotations

from typing import Self


class Inventory:
    __slots__ = ("counts",)

    def __init__(self, counts: dict[str, int] | None = None) -> None:
        self.counts: dict[str, int] = dict(counts or {})

    def count(self, item_id: str) -> int:
        return self.counts.get(item_id, 0)

    def add(self, item_id: str, amount: int) -> None:
        if amount <= 0:
            return
        self.counts[item_id] = self.counts.get(item_id, 0) + amount

    def remove(self, item_id: str, amount: int) -> bool:
        if self.count(item_id) < amount:
            return False
        n = self.counts[item_id] - amount
        if n <= 0:
            del self.counts[item_id]
        else:
            self.counts[item_id] = n
        return True

    def has(self, needs: dict[str, int]) -> bool:
        return all(self.count(k) >= v for k, v in needs.items())

    def consume(self, needs: dict[str, int]) -> bool:
        if not self.has(needs):
            return False
        for k, v in needs.items():
            self.remove(k, v)
        return True

    def copy(self) -> Self:
        return self.__class__(dict(self.counts))
