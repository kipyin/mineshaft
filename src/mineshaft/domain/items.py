from __future__ import annotations

from dataclasses import dataclass
from typing import Final


class ItemId:
    """String item identifiers (avoid Enum for JSON simplicity)."""

    STICK = "stick"
    PLANK = "plank"
    COBBLESTONE = "cobblestone"
    COAL = "coal"
    IRON_ORE = "iron_ore"
    WOOD = "wood"
    RAW_MEAT = "raw_meat"
    COOKED_MEAT = "cooked_meat"
    APPLE = "apple"
    BREAD = "bread"
    TORCH = "torch"

    WOODEN_PICKAXE = "wooden_pickaxe"
    STONE_PICKAXE = "stone_pickaxe"
    WOODEN_SWORD = "wooden_sword"
    STONE_SWORD = "stone_sword"

    FURNACE = "furnace"
    GOLD_NUGGET = "gold_nugget"
    BLAZE_POWDER = "blaze_powder"
    ENDER_PEARL = "ender_pearl"
    EYE_OF_ENDER = "eye_of_ender"


ITEM_DISPLAY: Final[dict[str, str]] = {
    ItemId.STICK: "Stick",
    ItemId.PLANK: "Plank",
    ItemId.COBBLESTONE: "Cobblestone",
    ItemId.COAL: "Coal",
    ItemId.IRON_ORE: "Iron Ore",
    ItemId.WOOD: "Wood",
    ItemId.RAW_MEAT: "Raw Meat",
    ItemId.COOKED_MEAT: "Cooked Meat",
    ItemId.APPLE: "Apple",
    ItemId.BREAD: "Bread",
    ItemId.TORCH: "Torch",
    ItemId.WOODEN_PICKAXE: "Wooden Pickaxe",
    ItemId.STONE_PICKAXE: "Stone Pickaxe",
    ItemId.WOODEN_SWORD: "Wooden Sword",
    ItemId.STONE_SWORD: "Stone Sword",
    ItemId.FURNACE: "Furnace",
    ItemId.GOLD_NUGGET: "Gold Nugget",
    ItemId.BLAZE_POWDER: "Blaze Powder",
    ItemId.ENDER_PEARL: "Ender Pearl",
    ItemId.EYE_OF_ENDER: "Eye of Ender",
}


def item_name(item_id: str) -> str:
    return ITEM_DISPLAY.get(item_id, item_id)


@dataclass(frozen=True, slots=True)
class Recipe:
    needs: dict[str, int]
    produces: str
    count: int = 1


# Shapeless crafting table recipes
RECIPES: tuple[Recipe, ...] = (
    Recipe({ItemId.WOOD: 1}, ItemId.PLANK, 4),
    Recipe({ItemId.PLANK: 2}, ItemId.STICK, 4),
    Recipe({ItemId.STICK: 2, ItemId.PLANK: 3}, ItemId.WOODEN_PICKAXE, 1),
    Recipe({ItemId.STICK: 2, ItemId.COBBLESTONE: 3}, ItemId.STONE_PICKAXE, 1),
    Recipe({ItemId.STICK: 1, ItemId.PLANK: 2}, ItemId.WOODEN_SWORD, 1),
    Recipe({ItemId.STICK: 1, ItemId.COBBLESTONE: 2}, ItemId.STONE_SWORD, 1),
    Recipe({ItemId.COAL: 1, ItemId.STICK: 1}, ItemId.TORCH, 4),
    Recipe({ItemId.COBBLESTONE: 8}, ItemId.FURNACE, 1),
    Recipe({ItemId.RAW_MEAT: 1, ItemId.COAL: 1}, ItemId.COOKED_MEAT, 1),
    Recipe({ItemId.APPLE: 3}, ItemId.BREAD, 1),
    Recipe({ItemId.COAL: 8, ItemId.IRON_ORE: 1}, ItemId.GOLD_NUGGET, 2),
    Recipe(
        {ItemId.BLAZE_POWDER: 1, ItemId.ENDER_PEARL: 1},
        ItemId.EYE_OF_ENDER,
        1,
    ),
)
