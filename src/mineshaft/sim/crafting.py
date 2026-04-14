from __future__ import annotations

from mineshaft.domain.inventory import Inventory
from mineshaft.domain.items import RECIPES, Recipe


def can_craft(inv: Inventory, recipe: Recipe) -> bool:
    return inv.has(recipe.needs)


def try_craft(inv: Inventory, recipe: Recipe) -> bool:
    if not inv.consume(recipe.needs):
        return False
    inv.add(recipe.produces, recipe.count)
    return True


def list_craftable(inv: Inventory) -> list[tuple[int, Recipe]]:
    out: list[tuple[int, Recipe]] = []
    for i, r in enumerate(RECIPES):
        if can_craft(inv, r):
            out.append((i, r))
    return out
