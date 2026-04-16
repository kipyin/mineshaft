from __future__ import annotations

import random
import uuid

from mineshaft.domain.mob_catalog import MOBS
from mineshaft.domain.overworld import Overworld, OverworldMob
from mineshaft.domain.pos import Pos
from mineshaft.domain.tiles import BiomeKind, Tile, TileKind
from mineshaft.gen.noise import fbm2, unit_float


def _biome(seed: int, x: int, y: int, w: int, h: int) -> BiomeKind:
    u = fbm2(seed, x, y)
    vx = x / max(w - 1, 1)
    vy = y / max(h - 1, 1)
    if vx < 0.15 or vx > 0.85 or vy < 0.15 or vy > 0.85:
        return BiomeKind.MOUNTAINS
    if u < 0.25:
        return BiomeKind.DESERT
    if u < 0.55:
        return BiomeKind.PLAINS
    return BiomeKind.FOREST


def _tile_for_biome(b: BiomeKind, u: float) -> TileKind:
    if b is BiomeKind.DESERT:
        if u < 0.06:
            return TileKind.WATER
        return TileKind.SAND
    if b is BiomeKind.FOREST:
        if u < 0.04:
            return TileKind.WATER
        if u < 0.22:
            return TileKind.TREE
        if u < 0.65:
            return TileKind.GRASS
        return TileKind.DIRT
    if b is BiomeKind.MOUNTAINS:
        if u < 0.04:
            return TileKind.WATER
        if u < 0.78:
            return TileKind.STONE
        return TileKind.DIRT
    # plains
    if u < 0.06:
        return TileKind.WATER
    if u < 0.75:
        return TileKind.GRASS
    return TileKind.DIRT


def _maybe_ore(seed: int, x: int, y: int, base: TileKind) -> TileKind:
    if base != TileKind.STONE:
        return base
    u = unit_float(seed ^ 99, x, y)
    if u < 0.04:
        return TileKind.COAL_ORE
    if u < 0.055:
        return TileKind.IRON_ORE
    return base


def generate_overworld(
    rng: random.Random,
    seed: int,
    width: int = 64,
    height: int = 64,
    cave_count: int = 8,
) -> tuple[Overworld, tuple[int, int]]:
    biome: list[list[BiomeKind]] = []
    tiles: list[list[Tile]] = []
    for y in range(height):
        brow: list[BiomeKind] = []
        trow: list[Tile] = []
        for x in range(width):
            if x == 0 or y == 0 or x == width - 1 or y == height - 1:
                trow.append(Tile(TileKind.BEDROCK))
                brow.append(BiomeKind.MOUNTAINS)
                continue
            b = _biome(seed, x, y, width, height)
            u = unit_float(seed ^ 7, x, y)
            tk = _tile_for_biome(b, u)
            tk = _maybe_ore(seed, x, y, tk)
            trow.append(Tile(tk))
            brow.append(b)
        biome.append(brow)
        tiles.append(trow)

    cave_to_mineshaft_id: dict[tuple[int, int], str] = {}
    mobs: dict[tuple[int, int], OverworldMob] = {}

    # Find candidate cave tiles (grass/dirt, not near edges)
    candidates: list[tuple[int, int]] = []
    for y in range(2, height - 2):
        for x in range(2, width - 2):
            t = tiles[y][x].kind
            move_ok = not tiles[y][x].blocks_movement()
            if t in (TileKind.GRASS, TileKind.DIRT, TileKind.SAND) and move_ok:
                candidates.append((x, y))
    rng.shuffle(candidates)

    placed = 0
    for cx, cy in candidates:
        if placed >= cave_count:
            break
        ok = True
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if tiles[cy + dy][cx + dx].kind in (
                    TileKind.CAVE_ENTRANCE,
                    TileKind.NETHER_PORTAL,
                ):
                    ok = False
        if not ok:
            continue
        did = str(uuid.uuid4())
        tiles[cy][cx] = Tile(TileKind.CAVE_ENTRANCE)
        cave_to_mineshaft_id[(cx, cy)] = did
        placed += 1

    # Player start: first non-blocking inner tile
    px, py = width // 2, height // 2
    for attempt in range(width * height):
        x = 1 + (attempt // height) % (width - 2)
        y = 1 + attempt % (height - 2)
        if not tiles[y][x].blocks_movement():
            px, py = x, y
            break

    # Sparse overworld hostiles in forests at night-equivalent: random mobs
    sp = MOBS.overworld_static
    for _ in range(sp.attempts):
        x = rng.randrange(2, width - 2)
        y = rng.randrange(2, height - 2)
        if (x, y) == (px, py):
            continue
        if cave_to_mineshaft_id.get((x, y)):
            continue
        if tiles[y][x].blocks_movement():
            continue
        if biome[y][x] is not BiomeKind.FOREST:
            continue
        if rng.random() > sp.chance:
            continue
        kind = rng.choice(sp.kinds)
        hp = rng.randint(sp.hp_min, sp.hp_max)
        atk = rng.randint(sp.atk_min, sp.atk_max)
        if (x, y) not in mobs and (x, y) not in cave_to_mineshaft_id:
            mobs[(x, y)] = OverworldMob(kind=kind, hp=hp, max_hp=hp, atk=atk)

    ow = Overworld(
        width=width,
        height=height,
        tiles=tiles,
        biome=biome,
        cave_to_mineshaft_id=cave_to_mineshaft_id,
        mobs=mobs,
    )
    _place_nether_portal(rng, ow, px, py)
    return ow, (px, py)


def _place_nether_portal(rng: random.Random, ow: Overworld, spawn_x: int, spawn_y: int) -> None:
    """One Nether portal tile on the Overworld (top-down), away from spawn."""
    w, h = ow.width, ow.height
    candidates: list[tuple[int, int]] = []
    for y in range(2, h - 2):
        for x in range(2, w - 2):
            if abs(x - spawn_x) + abs(y - spawn_y) < 10:
                continue
            if (x, y) in ow.cave_to_mineshaft_id:
                continue
            t = ow.tile_at(Pos(x, y))
            if t.kind in (TileKind.GRASS, TileKind.DIRT) and not t.blocks_movement():
                candidates.append((x, y))
    rng.shuffle(candidates)
    if not candidates:
        return
    px, py = candidates[0]
    ow.set_tile(Pos(px, py), Tile(TileKind.NETHER_PORTAL))
