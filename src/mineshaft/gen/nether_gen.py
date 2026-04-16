from __future__ import annotations

import random

from mineshaft.domain.overworld import Overworld, OverworldMob
from mineshaft.domain.pos import Pos
from mineshaft.domain.tiles import BiomeKind, Tile, TileKind
from mineshaft.gen.noise import unit_float


def _tile_walkable(tiles: list[list[Tile]], x: int, y: int) -> bool:
    if x < 0 or y < 0 or y >= len(tiles) or x >= len(tiles[0]):
        return False
    return not tiles[y][x].blocks_movement()


def generate_nether_world(
    rng: random.Random,
    seed: int,
    width: int = 48,
    height: int = 48,
) -> tuple[Overworld, Pos]:
    """Top-down Nether: netherrack, soul sand, lava; return portal stand position."""
    biome: list[list[BiomeKind]] = []
    tiles: list[list[Tile]] = []
    for y in range(height):
        brow: list[BiomeKind] = []
        trow: list[Tile] = []
        for x in range(width):
            if x == 0 or y == 0 or x == width - 1 or y == height - 1:
                trow.append(Tile(TileKind.BEDROCK))
                brow.append(BiomeKind.NETHER)
                continue
            u = unit_float(seed ^ 0x4E455448, x, y)
            if u < 0.06:
                tk = TileKind.NETHER_LAVA
            elif u < 0.14:
                tk = TileKind.SOUL_SAND
            else:
                tk = TileKind.NETHERRACK
            trow.append(Tile(tk))
            brow.append(BiomeKind.NETHER)
        tiles.append(trow)
        biome.append(brow)

    px, py = width // 2, height // 2
    tiles[py][px] = Tile(TileKind.NETHER_PORTAL)
    # End gate: walkable tile away from center portal
    gx, gy = width - 4, height // 2
    if _tile_walkable(tiles, gx, gy):
        tiles[gy][gx] = Tile(TileKind.END_GATE)
    else:
        for cand in ((width - 5, height // 2 + 1), (width - 6, height // 2)):
            gx, gy = cand
            if _tile_walkable(tiles, gx, gy):
                tiles[gy][gx] = Tile(TileKind.END_GATE)
                break

    mobs: dict[tuple[int, int], OverworldMob] = {}
    for _ in range(18):
        x = rng.randrange(2, width - 2)
        y = rng.randrange(2, height - 2)
        if (x, y) == (px, py):
            continue
        if tiles[y][x].kind is TileKind.END_GATE:
            continue
        if tiles[y][x].blocks_movement():
            continue
        if rng.random() > 0.4:
            continue
        kind = rng.choice(["piglin", "blaze", "magma"])
        hp = rng.randint(5, 12)
        atk = rng.randint(2, 5)
        mobs[(x, y)] = OverworldMob(kind=kind, hp=hp, max_hp=hp, atk=atk)

    ow = Overworld(
        width=width,
        height=height,
        tiles=tiles,
        biome=biome,
        cave_to_mineshaft_id={},
        mobs=mobs,
    )
    # Stand beside portal on netherrack
    spawn = Pos(px, py)
    for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        np = Pos(px + dx, py + dy)
        if ow.in_bounds(np) and not ow.tile_at(np).blocks_movement():
            spawn = np
            break
    return ow, spawn
