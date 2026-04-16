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
        if mob_atk > 0:
            cur_p -= mob_atk + rng.randint(0, 1)
    return max(0, cur_p), max(0, cur_m), cur_m <= 0


def nether_player_damage(inv: Inventory) -> int:
    return melee_damage(inv)


# Backward-compatible name (nether uses former mineshaft room combat).
mineshaft_player_damage = nether_player_damage


def resolve_end_dragon_exchange(
    inv: Inventory,
    dragon_hp: int,
    player_hp: int,
    rng: random.Random,
    phase: int,
) -> tuple[int, int, int, bool]:
    """One player strike then dragon counter. Returns (dragon_hp, player_hp, phase, defeated)."""
    dragon_hp -= melee_damage(inv) + rng.randint(0, 2)
    if dragon_hp <= 0:
        return 0, player_hp, phase, True
    # phase 0: ground swipe; phase 1: breath (harder) — alternate each exchange
    if phase == 0:
        player_hp -= 5 + rng.randint(0, 2)
        new_phase = 1
    else:
        player_hp -= 7 + rng.randint(0, 3)
        new_phase = 0
    return dragon_hp, max(0, player_hp), new_phase, False
