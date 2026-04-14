from __future__ import annotations

from dataclasses import dataclass, field

from mineshaft.domain.pos import Pos
from mineshaft.domain.tiles import BiomeKind, Tile


@dataclass
class OverworldMob:
    kind: str
    hp: int
    max_hp: int
    atk: int


@dataclass
class Overworld:
    width: int
    height: int
    tiles: list[list[Tile]]
    biome: list[list[BiomeKind]]
    cave_to_mineshaft_id: dict[tuple[int, int], str]
    mobs: dict[tuple[int, int], OverworldMob] = field(default_factory=dict)

    def in_bounds(self, pos: Pos) -> bool:
        return 0 <= pos.x < self.width and 0 <= pos.y < self.height

    def tile_at(self, pos: Pos) -> Tile:
        return self.tiles[pos.y][pos.x]

    def biome_at(self, pos: Pos) -> BiomeKind:
        return self.biome[pos.y][pos.x]

    def set_tile(self, pos: Pos, tile: Tile) -> None:
        self.tiles[pos.y][pos.x] = tile


def first_walkable_inner_tile(ow: Overworld) -> Pos:
    """First walkable inner tile (same scan order as overworld generation)."""
    w, h = ow.width, ow.height
    for attempt in range(w * h):
        x = 1 + (attempt // h) % (w - 2)
        y = 1 + attempt % (h - 2)
        if not ow.tile_at(Pos(x, y)).blocks_movement():
            return Pos(x, y)
    return Pos(w // 2, h // 2)
