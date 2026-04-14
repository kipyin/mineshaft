from __future__ import annotations

import random

from mineshaft.domain.inventory import Inventory
from mineshaft.domain.items import ItemId
from mineshaft.domain.tiles import Tile, TileKind


def pickaxe_tier(inv: Inventory) -> int:
    if inv.count(ItemId.STONE_PICKAXE) > 0:
        return 2
    if inv.count(ItemId.WOODEN_PICKAXE) > 0:
        return 1
    return 0


def can_mine_tile(inv: Inventory, kind: TileKind) -> bool:
    tier = pickaxe_tier(inv)
    if kind is TileKind.IRON_ORE:
        return tier >= 2
    if kind in (TileKind.STONE, TileKind.COAL_ORE):
        return tier >= 1
    if kind in (TileKind.TREE, TileKind.DIRT, TileKind.GRASS, TileKind.SAND):
        return True
    return False


def mine_tile(
    inv: Inventory,
    rng: random.Random,
    tile: Tile,
) -> tuple[Tile, list[tuple[str, int]]]:
    """Return replacement tile and drops."""
    k = tile.kind
    drops: list[tuple[str, int]] = []

    if k is TileKind.GRASS:
        if rng.random() < 0.08:
            drops.append((ItemId.APPLE, 1))
        return Tile(TileKind.DIRT), drops

    if k is TileKind.TREE:
        return Tile(TileKind.GRASS), [(ItemId.WOOD, 1)]

    if k in (TileKind.DIRT, TileKind.SAND):
        return Tile(tile.kind), []

    if k is TileKind.STONE:
        return Tile(TileKind.DIRT), [(ItemId.COBBLESTONE, rng.randint(1, 2))]

    if k is TileKind.COAL_ORE:
        return Tile(TileKind.DIRT), [(ItemId.COAL, rng.randint(1, 3))]

    if k is TileKind.IRON_ORE:
        return Tile(TileKind.DIRT), [(ItemId.IRON_ORE, 1)]

    return tile, []
