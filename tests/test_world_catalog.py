from __future__ import annotations

from pathlib import Path

import pytest

from mineshaft.domain import mob_catalog as mob_catalog_mod
from mineshaft.domain.mob_catalog import load_bundled_mobs_dict, parse_mobs_dict
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
    assert "crawler" in m.overworld_static.kinds
    assert len(m.mineshaft_pool) == 3


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
                "[overworld.static_spawns]",
                'attempts = 1',
                "chance = 1",
                'kinds = ["a"]',
                "hp_min = 1",
                "hp_max = 1",
                "atk_min = 1",
                "atk_max = 1",
                "",
                "[overworld.random_encounter]",
                "chance = 1",
                'kinds = ["b"]',
                "hp_min = 1",
                "hp_max = 1",
                "atk_min = 1",
                "atk_max = 1",
                "",
                "[nether.static_spawns]",
                'attempts = 1',
                "chance = 1",
                'kinds = ["c"]',
                "hp_min = 1",
                "hp_max = 1",
                "atk_min = 1",
                "atk_max = 1",
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
    finally:
        monkeypatch.chdir(tmp_path)
        mob_catalog_mod.reload_mob_catalog()
