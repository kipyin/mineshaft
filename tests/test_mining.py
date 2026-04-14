from __future__ import annotations

import random

from mineshaft.domain.inventory import Inventory
from mineshaft.domain.items import ItemId
from mineshaft.domain.tiles import Tile, TileKind
from mineshaft.sim.mining import can_mine_tile, mine_tile, pickaxe_tier


def test_pickaxe_tiers() -> None:
    inv = Inventory()
    assert pickaxe_tier(inv) == 0
    inv.add(ItemId.WOODEN_PICKAXE, 1)
    assert pickaxe_tier(inv) == 1
    inv.add(ItemId.STONE_PICKAXE, 1)
    assert pickaxe_tier(inv) == 2


def test_iron_requires_stone_pick() -> None:
    inv = Inventory({ItemId.WOODEN_PICKAXE: 1})
    assert can_mine_tile(inv, TileKind.IRON_ORE) is False
    inv.add(ItemId.STONE_PICKAXE, 1)
    assert can_mine_tile(inv, TileKind.IRON_ORE) is True


def test_mine_stone_drops_cobble() -> None:
    inv = Inventory({ItemId.WOODEN_PICKAXE: 1})
    rng = random.Random(1)
    tnew, drops = mine_tile(inv, rng, Tile(TileKind.STONE))
    assert tnew.kind is TileKind.DIRT
    assert ItemId.COBBLESTONE in [d[0] for d in drops]
