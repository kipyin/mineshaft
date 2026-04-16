from __future__ import annotations

from enum import Enum

from mineshaft.domain.tile_catalog import BLOCKS_MOVEMENT, NOT_MINEABLE


class BiomeKind(Enum):
    PLAINS = "plains"
    FOREST = "forest"
    DESERT = "desert"
    MOUNTAINS = "mountains"
    NETHER = "nether"
    END = "end"


class TileKind(Enum):
    GRASS = "grass"
    DIRT = "dirt"
    STONE = "stone"
    SAND = "sand"
    WATER = "water"
    TREE = "tree"
    COAL_ORE = "coal_ore"
    IRON_ORE = "iron_ore"
    CAVE_ENTRANCE = "cave_entrance"
    BEDROCK = "bedrock"
    NETHER_PORTAL = "nether_portal"
    NETHERRACK = "netherrack"
    SOUL_SAND = "soul_sand"
    NETHER_LAVA = "nether_lava"
    END_GATE = "end_gate"
    END_STONE = "end_stone"


class Tile:
    __slots__ = ("kind",)

    def __init__(self, kind: TileKind) -> None:
        self.kind = kind

    def blocks_movement(self) -> bool:
        return self.kind.value in BLOCKS_MOVEMENT

    def mineable(self) -> bool:
        return self.kind.value not in NOT_MINEABLE
