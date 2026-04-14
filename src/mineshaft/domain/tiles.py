from __future__ import annotations

from enum import Enum


class BiomeKind(Enum):
    PLAINS = "plains"
    FOREST = "forest"
    DESERT = "desert"
    MOUNTAINS = "mountains"


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


class Tile:
    __slots__ = ("kind",)

    def __init__(self, kind: TileKind) -> None:
        self.kind = kind

    def blocks_movement(self) -> bool:
        return self.kind in (TileKind.WATER, TileKind.TREE, TileKind.BEDROCK)

    def mineable(self) -> bool:
        return self.kind not in (
            TileKind.WATER,
            TileKind.BEDROCK,
            TileKind.GRASS,
            TileKind.CAVE_ENTRANCE,
        )


def tile_glyph(kind: TileKind) -> str:
    return {
        TileKind.GRASS: '"',
        TileKind.DIRT: ":",
        TileKind.STONE: "#",
        TileKind.SAND: "~",
        TileKind.WATER: "≈",
        TileKind.TREE: "T",
        TileKind.COAL_ORE: "◆",
        TileKind.IRON_ORE: "◇",
        TileKind.CAVE_ENTRANCE: "Ω",
        TileKind.BEDROCK: "█",
    }[kind]
