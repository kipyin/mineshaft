from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal

from mineshaft.domain.direction import Direction
from mineshaft.domain.inventory import Inventory
from mineshaft.domain.mineshaft_run import MineshaftRoom, MineshaftRun
from mineshaft.domain.overworld import Overworld, OverworldMob, first_walkable_inner_tile
from mineshaft.domain.player import Player
from mineshaft.domain.pos import Pos
from mineshaft.domain.tiles import BiomeKind, Tile, TileKind
from mineshaft.sim.engine import Game

SCHEMA_VERSION = 2


def _tile_to_json(t: Tile) -> str:
    return t.kind.name


def _tile_from_json(s: str) -> Tile:
    return Tile(TileKind[s])


def _serialize_overworld(ow: Overworld) -> dict[str, Any]:
    return {
        "width": ow.width,
        "height": ow.height,
        "tiles": [[_tile_to_json(t) for t in row] for row in ow.tiles],
        "biome": [[b.name for b in row] for row in ow.biome],
        "cave_to_mineshaft_id": {f"{x},{y}": v for (x, y), v in ow.cave_to_mineshaft_id.items()},
        "mobs": {
            f"{x},{y}": {"kind": m.kind, "hp": m.hp, "max_hp": m.max_hp, "atk": m.atk}
            for (x, y), m in ow.mobs.items()
        },
    }


def _deserialize_overworld(d: dict[str, Any]) -> Overworld:
    w, h = d["width"], d["height"]
    tiles: list[list[Tile]] = [
        [_tile_from_json(c) for c in row] for row in d["tiles"]
    ]
    biome: list[list[BiomeKind]] = [
        [BiomeKind[b] for b in row] for row in d["biome"]
    ]
    if "cave_to_mineshaft_id" in d:
        cave_raw = d["cave_to_mineshaft_id"]
    else:
        cave_raw = d["cave_to_dungeon"]
    cave_to_mineshaft_id: dict[tuple[int, int], str] = {}
    for k, v in cave_raw.items():
        xs, ys = k.split(",")
        cave_to_mineshaft_id[(int(xs), int(ys))] = v
    mobs: dict[tuple[int, int], OverworldMob] = {}
    for k, m in d["mobs"].items():
        xs, ys = k.split(",")
        mobs[(int(xs), int(ys))] = OverworldMob(
            kind=m["kind"], hp=m["hp"], max_hp=m["max_hp"], atk=m["atk"]
        )
    return Overworld(
        width=w,
        height=h,
        tiles=tiles,
        biome=biome,
        cave_to_mineshaft_id=cave_to_mineshaft_id,
        mobs=mobs,
    )


def _serialize_mineshaft_run(run: MineshaftRun) -> dict[str, Any]:
    rooms = {k: asdict(v) for k, v in run.rooms.items()}
    return {
        "mineshaft_id": run.mineshaft_id,
        "tier": run.tier,
        "rooms": rooms,
        "current_room": run.current_room,
        "entrance_room_id": run.entrance_room_id,
        "overworld_return": list(run.overworld_return),
        "visited_room_ids": list(run.visited_room_ids),
    }


def _deserialize_mineshaft_run(d: dict[str, Any]) -> MineshaftRun:
    rooms_raw = d["rooms"]
    mid = d.get("mineshaft_id") or d.get("dungeon_id")
    if not mid:
        raise ValueError("mineshaft save missing mineshaft_id / dungeon_id")
    rooms: dict[str, MineshaftRoom] = {}
    for rid, rr in rooms_raw.items():
        rooms[rid] = MineshaftRoom(**rr)
    ox, oy = d["overworld_return"]
    visited = list(d.get("visited_room_ids") or [])
    cur = d["current_room"]
    if cur and cur not in visited:
        visited.append(cur)
    return MineshaftRun(
        mineshaft_id=mid,
        tier=d["tier"],
        rooms=rooms,
        current_room=cur,
        entrance_room_id=d["entrance_room_id"],
        overworld_return=(int(ox), int(oy)),
        visited_room_ids=visited,
    )


def _normalize_mode(raw: str) -> Literal["overworld", "mineshaft"]:
    if raw == "dungeon":
        return "mineshaft"
    if raw in ("overworld", "mineshaft"):
        return raw
    raise ValueError(f"Unknown mode in save: {raw!r}")


def _serialize_player(p: Player) -> dict[str, Any]:
    return {
        "pos": [p.pos.x, p.pos.y],
        "facing": p.facing.name,
        "hp": p.hp,
        "max_hp": p.max_hp,
        "hunger": p.hunger,
        "max_hunger": p.max_hunger,
        "inventory": dict(p.inventory.counts),
    }


def _deserialize_player(d: dict[str, Any]) -> Player:
    x, y = d["pos"]
    return Player(
        pos=Pos(x, y),
        facing=Direction[d["facing"]],
        hp=d["hp"],
        max_hp=d["max_hp"],
        hunger=d["hunger"],
        max_hunger=d["max_hunger"],
        inventory=Inventory(dict(d["inventory"])),
    )


def save_game(path: Path, game: Game) -> None:
    data: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "seed": game.seed,
        "mode": game.mode,
        "overworld": _serialize_overworld(game.overworld),
        "player": _serialize_player(game.player),
        "spawn_pos": [game.spawn_pos.x, game.spawn_pos.y],
        "mineshaft_runs": {k: _serialize_mineshaft_run(v) for k, v in game.mineshaft_runs.items()},
        "active_mineshaft_id": game.mineshaft_run.mineshaft_id if game.mineshaft_run else None,
        "saved_entrance_facing": game.saved_entrance_facing.name,
        "moves_since_hunger": game.moves_since_hunger,
        "world_time_ticks": game.world_time_ticks,
        "log": game.log_lines,
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_game(path: Path) -> Game:
    raw = json.loads(path.read_text(encoding="utf-8"))
    sv = int(raw.get("schema_version", 1))
    if sv < 1 or sv > SCHEMA_VERSION:
        raise ValueError(f"Unsupported save schema: {sv}")

    ow = _deserialize_overworld(raw["overworld"])
    player = _deserialize_player(raw["player"])
    if "spawn_pos" in raw:
        sx, sy = raw["spawn_pos"]
        spawn_pos = Pos(int(sx), int(sy))
    else:
        spawn_pos = first_walkable_inner_tile(ow)
    runs_raw = raw.get("mineshaft_runs", raw.get("dungeons", {}))
    mineshaft_runs = {k: _deserialize_mineshaft_run(v) for k, v in runs_raw.items()}
    aid = raw.get("active_mineshaft_id", raw.get("active_dungeon_id"))
    active = mineshaft_runs[aid] if aid else None
    g = Game.from_snapshot(
        seed=raw["seed"],
        overworld=ow,
        player=player,
        spawn_pos=spawn_pos,
        mode=_normalize_mode(raw["mode"]),
        mineshaft_runs=mineshaft_runs,
        mineshaft_run=active,
        saved_entrance_facing=Direction[raw["saved_entrance_facing"]],
        moves_since_hunger=raw.get("moves_since_hunger", 0),
        world_time_ticks=raw.get("world_time_ticks", 0),
        log=list(raw.get("log", [])),
    )
    if g.player.hp <= 0:
        g.player.hp = g.player.max_hp
        g.player.hunger = g.player.max_hunger
        if g.mode == "mineshaft":
            g.mode = "overworld"
            g.mineshaft_run = None
        g.player.pos = Pos(g.spawn_pos.x, g.spawn_pos.y)
    return g
