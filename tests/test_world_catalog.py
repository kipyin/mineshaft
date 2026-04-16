from __future__ import annotations

from pathlib import Path

import pytest

from mineshaft.domain import mob_catalog as mob_catalog_mod
from mineshaft.domain.mob_catalog import (
    apply_mob_drops,
    load_bundled_mobs_dict,
    parse_mobs_dict,
)
from mineshaft.domain.tile_catalog import (
    load_bundled_tiles_dict,
    parse_tiles_dict,
    resolve_tiles_path,
)
from mineshaft.domain.tiles import Tile, TileKind


def test_tile_rules_from_bundled() -> None:
    bm, nm, _, _ = parse_tiles_dict(load_bundled_tiles_dict())
    assert "water" in bm
    assert "bedrock" in nm


def test_tile_blocks_movement() -> None:
    assert Tile(TileKind.WATER).blocks_movement() is True
    assert Tile(TileKind.GRASS).blocks_movement() is False


def test_mobs_bundled_parse() -> None:
    m = parse_mobs_dict(load_bundled_mobs_dict())
    assert "zombie" in m.definitions
    assert m.boss_ender_dragon_hp == 200
    assert "zombie" in m.overworld_static_forest.kinds
    assert "pig" in m.overworld_static_plains.kinds
    assert len(m.mineshaft_pool) == 3


def test_mobs_spawn_kinds_exist_in_definitions() -> None:
    m = parse_mobs_dict(load_bundled_mobs_dict())
    for pool in (
        m.overworld_static_forest.kinds,
        m.overworld_static_plains.kinds,
        m.overworld_encounter.kinds,
        m.nether_static.kinds,
        m.mineshaft_pool,
    ):
        for k in pool:
            assert k in m.definitions


def test_apply_mob_drops_deterministic() -> None:
    import random

    from mineshaft.domain.inventory import Inventory
    from mineshaft.domain.mob_catalog import MobDefinition, MobDrop

    inv = Inventory()
    d = MobDefinition(
        kind_id="t",
        hp=1,
        atk=1,
        hostile=True,
        drops=(MobDrop("coal", 1.0, 1, 1),),
    )
    rng = random.Random(0)
    gained = apply_mob_drops(rng, inv, d)
    assert gained == [("coal", 1)]
    assert inv.count("coal") == 1


def test_resolve_tiles_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    p = tmp_path / "t.toml"
    body = (
        "[rules]\nblocks_movement = []\nnot_mineable = []\n"
        '[tile_render.x]\nchar="█"\nstyle="white on black"\n'
    )
    p.write_text(body, encoding="utf-8")
    monkeypatch.setenv("MINESHAFT_TILES", str(p))
    assert resolve_tiles_path() == p


def test_reload_mob_catalog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p = tmp_path / "m.toml"
    p.write_text(
        "\n".join(
            [
                "[boss.ender_dragon]",
                "hp = 99",
                "",
                "[definitions.a]",
                "hp = 1",
                "atk = 1",
                "hostile = true",
                "",
                "[definitions.b]",
                "hp = 1",
                "atk = 1",
                "hostile = true",
                "",
                "[definitions.c]",
                "hp = 1",
                "atk = 1",
                "hostile = true",
                "",
                "[definitions.x]",
                "hp = 1",
                "atk = 0",
                "hostile = false",
                "",
                "[overworld.static_spawns_forest]",
                "attempts = 1",
                "chance = 1",
                'kinds = ["a"]',
                "",
                "[overworld.static_spawns_plains]",
                "attempts = 1",
                "chance = 1",
                'kinds = ["b"]',
                "",
                "[overworld.random_encounter]",
                "chance = 1",
                'kinds = ["a"]',
                "",
                "[nether.static_spawns]",
                "attempts = 1",
                "chance = 1",
                'kinds = ["c"]',
                "",
                "[mineshaft]",
                'room_mob_pool = ["x"]',
                "",
            ]
        ),
        encoding="utf-8",
    )
    try:
        mob_catalog_mod.reload_mob_catalog(p)
        assert mob_catalog_mod.MOBS.mineshaft_pool == ("x",)
        assert mob_catalog_mod.MOBS.boss_ender_dragon_hp == 99
    finally:
        monkeypatch.chdir(tmp_path)
        mob_catalog_mod.reload_mob_catalog()
