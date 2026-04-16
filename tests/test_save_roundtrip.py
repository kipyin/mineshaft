from __future__ import annotations

import json
from pathlib import Path

from mineshaft.persistence.save import load_game, save_game
from mineshaft.sim.engine import Game


def test_save_roundtrip(tmp_path: Path) -> None:
    g1 = Game(seed=4242)
    g1.player.inventory.add("stick", 3)
    g1.world_time_ticks = 12345
    p = tmp_path / "s.json"
    save_game(p, g1)
    g2 = load_game(p)
    assert g2.seed == g1.seed
    assert g2.player.inventory.count("stick") == 3
    assert g2.dimension == g1.dimension
    assert g2.mc_game_mode == g1.mc_game_mode
    assert g2.world_time_ticks == 12345
    assert g2.spawn_pos.x == g1.spawn_pos.x and g2.spawn_pos.y == g1.spawn_pos.y


def test_new_save_schema_and_keys(tmp_path: Path) -> None:
    g = Game(seed=7)
    p = tmp_path / "out.json"
    save_game(p, g)
    raw = json.loads(p.read_text())
    assert raw["dimension"] in ("overworld", "dungeon", "nether", "end")
    assert raw["mc_game_mode"] in ("survival", "creative", "adventure", "spectator")
    assert raw["schema_version"] == 4
    assert "spawn_pos" in raw
    assert "mineshaft_runs" in raw
    assert "active_mineshaft_id" in raw
    assert "cave_to_mineshaft_id" in raw["overworld"]
    for run in raw["mineshaft_runs"].values():
        assert "mineshaft_id" in run
    assert "victory" in raw
    assert "end_run" in raw


def test_legacy_dungeon_named_keys_still_load(tmp_path: Path) -> None:
    """Pre-rename saves used dungeon*, cave_to_dungeon, nested dungeon_id, mode 'dungeon'."""
    g_src = Game(seed=123)
    p_new = tmp_path / "current.json"
    save_game(p_new, g_src)
    raw = json.loads(p_new.read_text())

    ow = dict(raw["overworld"])
    cts = ow.pop("cave_to_mineshaft_id")
    dungeons: dict[str, object] = {}
    for k, run in raw["mineshaft_runs"].items():
        rr = dict(run)
        rr["dungeon_id"] = rr.pop("mineshaft_id")
        dungeons[k] = rr

    legacy = {
        "schema_version": raw["schema_version"],
        "seed": raw["seed"],
        "mode": raw.get("mode", raw.get("dimension", "overworld")),
        "overworld": {**ow, "cave_to_dungeon": cts},
        "player": raw["player"],
        "dungeons": dungeons,
        "active_dungeon_id": raw["active_mineshaft_id"],
        "saved_entrance_facing": raw["saved_entrance_facing"],
        "moves_since_hunger": raw["moves_since_hunger"],
        "log": raw["log"],
    }
    p_old = tmp_path / "legacy.json"
    p_old.write_text(json.dumps(legacy), encoding="utf-8")
    g_old = load_game(p_old)
    assert g_old.dimension == g_src.dimension
    assert g_old.seed == g_src.seed
    assert g_src.player.pos.x == g_old.player.pos.x
    assert g_old.overworld.cave_to_mineshaft_id == g_src.overworld.cave_to_mineshaft_id
    assert g_old.world_time_ticks == 0
