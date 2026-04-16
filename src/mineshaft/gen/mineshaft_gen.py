from __future__ import annotations

import random

from mineshaft.domain.items import ItemId
from mineshaft.domain.mineshaft_run import MineshaftRoom, MineshaftRun
from mineshaft.domain.mob_catalog import MOBS


def generate_mineshaft(
    rng: random.Random,
    mineshaft_id: str,
    tier: int,
    overworld_return: tuple[int, int],
    room_count: int = 12,
) -> MineshaftRun:
    room_ids = [f"r{i}" for i in range(room_count)]
    entrance = room_ids[0]
    escape = room_ids[-1]

    exits: dict[str, dict[str, str]] = {rid: {} for rid in room_ids}

    def link(a: str, dir_a: str, b: str, dir_b: str) -> None:
        if dir_a in exits[a] or dir_b in exits[b]:
            return
        exits[a][dir_a] = b
        exits[b][dir_b] = a

    # Main corridor: east/west alternation
    for i in range(room_count - 1):
        a, b = room_ids[i], room_ids[i + 1]
        forward = "east" if i % 2 == 0 else "south"
        backward = {"east": "west", "west": "east", "north": "south", "south": "north"}[
            forward
        ]
        link(a, forward, b, backward)

    # Random extra links
    for _ in range(max(2, room_count // 4)):
        i = rng.randrange(0, room_count - 2)
        a, b = room_ids[i], room_ids[i + 2]
        dirs = [("north", "south"), ("south", "north"), ("east", "west"), ("west", "east")]
        da, db = rng.choice(dirs)
        link(a, da, b, db)

    rooms: dict[str, MineshaftRoom] = {}
    for i, rid in enumerate(room_ids):
        depth = i
        mob_kind = None
        mob_hp = 0
        mob_max = 0
        mob_atk = 0
        loot = None
        is_entrance = rid == entrance
        exit_world = rid == escape

        if not is_entrance:
            if rng.random() < 0.68:
                mob_kind = rng.choice(MOBS.mineshaft_pool)
                scale = 1 + tier + min(depth // 4, 5)
                mob_max = rng.randint(5, 10) + scale
                mob_hp = mob_max
                mob_atk = rng.randint(1, 4) + tier

        if mob_kind is None and not is_entrance and rng.random() < 0.38:
            loot = rng.choice(
                [
                    ItemId.COAL,
                    ItemId.IRON_ORE,
                    ItemId.APPLE,
                    ItemId.RAW_MEAT,
                    ItemId.TORCH,
                    ItemId.GOLD_NUGGET,
                    ItemId.ENDER_PEARL,
                ]
            )

        title = f"Collapsed tunnel {i + 1}"
        if is_entrance:
            title = "Mineshaft entrance"
        elif exit_world:
            title = "Escape shaft"
        elif mob_kind:
            title = f"Infested corridor ({mob_kind})"

        rooms[rid] = MineshaftRoom(
            id=rid,
            title=title,
            depth=depth,
            exits=dict(exits.get(rid, {})),
            mob_kind=mob_kind,
            mob_hp=mob_hp,
            mob_max_hp=mob_max,
            mob_atk=mob_atk,
            loot_id=loot,
            loot_taken=False,
            is_entrance=is_entrance,
            exit_to_overworld=exit_world,
            exit_to_end_portal=False,
        )

    return MineshaftRun(
        mineshaft_id=mineshaft_id,
        tier=tier,
        rooms=rooms,
        current_room=entrance,
        entrance_room_id=entrance,
        overworld_return=overworld_return,
    )
