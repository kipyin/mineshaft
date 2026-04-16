from __future__ import annotations

import random

from mineshaft.domain.overworld import Overworld
from mineshaft.domain.pos import Pos
from mineshaft.domain.tiles import BiomeKind, Tile, TileKind


def generate_end_world(
    rng: random.Random,
    seed: int,
    size: int = 28,
) -> tuple[Overworld, Pos, Pos]:
    """Top-down End: end stone island; dragon position at center (combat via Space + end_run)."""
    biome = [[BiomeKind.END for _ in range(size)] for _ in range(size)]
    tiles: list[list[Tile]] = []
    for y in range(size):
        row: list[Tile] = []
        for x in range(size):
            if x == 0 or y == 0 or x == size - 1 or y == size - 1:
                row.append(Tile(TileKind.BEDROCK))
            else:
                row.append(Tile(TileKind.END_STONE))
        tiles.append(row)

    cx, cy = size // 2, size // 2
    dragon_pos = Pos(cx, cy)
    # Spawn south of dragon
    spawn = Pos(cx, cy + 2)
    if spawn.y >= size - 1 or tiles[spawn.y][spawn.x].blocks_movement():
        spawn = Pos(cx, cy - 2)

    ow = Overworld(
        width=size,
        height=size,
        tiles=tiles,
        biome=biome,
        cave_to_mineshaft_id={},
        mobs={},
    )
    return ow, spawn, dragon_pos
