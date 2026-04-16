"""Dimensions (overworld / dungeon / nether / end) and dragon combat."""

from __future__ import annotations

import json
from pathlib import Path

from mineshaft.domain import mob_catalog as mob_catalog_mod
from mineshaft.domain.direction import Direction
from mineshaft.domain.end_run import EndRun
from mineshaft.domain.items import ItemId
from mineshaft.domain.overworld import Overworld
from mineshaft.domain.player import Player
from mineshaft.domain.pos import Pos
from mineshaft.domain.tiles import BiomeKind, Tile, TileKind
from mineshaft.gen.nether_gen import generate_nether_world
from mineshaft.persistence.save import load_game, save_game
from mineshaft.sim.combat import resolve_end_dragon_exchange
from mineshaft.sim.engine import EYES_FOR_END, Game


def test_legacy_mode_mineshaft_loads_as_dungeon(tmp_path: Path) -> None:
    g = Game(seed=99)
    p = tmp_path / "legacy_mode.json"
    save_game(p, g)
    raw = json.loads(p.read_text())
    raw["mode"] = "mineshaft"
    raw["schema_version"] = 2
    raw.pop("dimension", None)
    p.write_text(json.dumps(raw), encoding="utf-8")
    g2 = load_game(p)
    assert g2.dimension == "dungeon"


def test_end_dragon_exchange_defeats_at_zero_hp() -> None:
    import random

    rng = random.Random(0)
    inv = Player(pos=Pos(0, 0), facing=Direction.N).inventory
    d_hp, p_hp, _ph, defeated = resolve_end_dragon_exchange(inv, 1, 20, rng, 0)
    assert defeated
    assert d_hp == 0
    assert p_hp == 20


def test_enter_end_from_nether_topdown_consumes_eyes() -> None:
    """Standing on End gate in Nether with eyes enters The End (top-down)."""
    rng = __import__("random").Random(0)
    nw, _ = generate_nether_world(rng, 42)
    # Find an END_GATE tile
    gp: Pos | None = None
    for y in range(nw.height):
        for x in range(nw.width):
            if nw.tile_at(Pos(x, y)).kind is TileKind.END_GATE:
                gp = Pos(x, y)
                break
        if gp:
            break
    assert gp is not None
    ow = Overworld(
        width=5,
        height=5,
        tiles=[[Tile(TileKind.GRASS) for _ in range(5)] for _ in range(5)],
        biome=[[BiomeKind.PLAINS for _ in range(5)] for _ in range(5)],
        cave_to_mineshaft_id={},
        mobs={},
    )
    p = Player(pos=gp, facing=Direction.N)
    g = Game.from_snapshot(
        seed=1,
        overworld=ow,
        player=p,
        spawn_pos=Pos(1, 1),
        dimension="nether",
        mc_game_mode="survival",
        mineshaft_runs={},
        mineshaft_run=None,
        saved_entrance_facing=Direction.N,
        overworld_nether_portal_pos=Pos(2, 2),
        nether_spawn_pos=Pos(1, 1),
        nether_world=nw,
        end_world=None,
        end_dragon_pos=None,
        end_entry_spawn=None,
        moves_since_hunger=0,
        world_time_ticks=0,
        log=[],
    )
    g.player.pos = gp
    g.player.inventory.add(ItemId.EYE_OF_ENDER, EYES_FOR_END)
    g.interact()
    assert g.dimension == "end"
    assert g.end_run is not None
    assert g.end_run.dragon_hp == mob_catalog_mod.MOBS.boss_ender_dragon_hp
    assert g.player.inventory.count(ItemId.EYE_OF_ENDER) == 0


def test_save_roundtrip_end_state(tmp_path: Path) -> None:
    from mineshaft.gen.end_gen import generate_end_world

    g = Game(seed=5)
    g.end_world, esp, dpos = generate_end_world(__import__("random").Random(1), 5)
    g.end_dragon_pos = dpos
    g.end_entry_spawn = esp
    g.dimension = "end"
    g.end_run = EndRun(
        dragon_hp=40,
        dragon_max_hp=mob_catalog_mod.MOBS.boss_ender_dragon_hp,
        phase=1,
    )
    g.victory = False
    g.mineshaft_run = None
    g.player.pos = Pos(esp.x, esp.y)
    p = tmp_path / "end.json"
    save_game(p, g)
    g2 = load_game(p)
    assert g2.dimension == "end"
    assert g2.end_run is not None
    assert g2.end_run.dragon_hp == 40
    assert g2.end_run.phase == 1
    assert g2.victory is False
