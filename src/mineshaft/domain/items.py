from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mineshaft.domain.item_catalog import (
    load_catalog_dict,
    parse_catalog_dict,
    resolve_catalog_path,
)


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


def item_name(item_id: str) -> str:
    return ITEM_DISPLAY.get(item_id, item_id)


@dataclass(frozen=True, slots=True)
class Recipe:
    needs: dict[str, int]
    produces: str
    count: int = 1


def _recipes_from_rows(
    rows: list[tuple[dict[str, int], str, int]],
) -> tuple[Recipe, ...]:
    return tuple(Recipe(needs, produces, count) for needs, produces, count in rows)


def _build_catalog(data: dict) -> tuple[dict[str, str], tuple[Recipe, ...]]:
    display, rows = parse_catalog_dict(data)
    return display, _recipes_from_rows(rows)


def load_item_catalog(path: Path | None = None) -> tuple[dict[str, str], tuple[Recipe, ...]]:
    """Load display names and recipes from TOML or YAML.

    ``path`` — explicit file, or ``None`` to use ``MINESHAFT_ITEMS``, then
    ``./mineshaft_items.{toml,yaml,yml}``, then the bundled default.
    """
    if path is not None:
        data = load_catalog_dict(path)
    else:
        resolved = resolve_catalog_path()
        data = load_catalog_dict(resolved)
    return _build_catalog(data)


ITEM_DISPLAY, RECIPES = load_item_catalog()


def reload_item_catalog(path: Path | None = None) -> None:
    """Replace ``ITEM_DISPLAY`` and ``RECIPES`` (e.g. for modding or tests)."""
    global ITEM_DISPLAY, RECIPES
    ITEM_DISPLAY, RECIPES = load_item_catalog(path)
