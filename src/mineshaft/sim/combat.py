from __future__ import annotations

import random

from mineshaft.domain.inventory import Inventory
from mineshaft.domain.items import ItemId


def melee_damage(inv: Inventory) -> int:
    if inv.count(ItemId.STONE_SWORD) > 0:
        return 5
    if inv.count(ItemId.WOODEN_SWORD) > 0:
        return 3
    return 2


def resolve_overworld_melee(
    inv: Inventory,
    mob_hp: int,
    mob_atk: int,
    player_hp: int,
    rng: random.Random,
) -> tuple[int, int, bool]:
    """Returns (new_player_hp, remaining_mob_hp, mob_defeated)."""
    cur_p = player_hp
    cur_m = mob_hp
    while cur_m > 0 and cur_p > 0:
        cur_m -= melee_damage(inv) + rng.randint(0, 2)
        if cur_m <= 0:
            return cur_p, 0, True
        cur_p -= mob_atk + rng.randint(0, 1)
    return max(0, cur_p), max(0, cur_m), cur_m <= 0


def mineshaft_player_damage(inv: Inventory) -> int:
    return melee_damage(inv)
