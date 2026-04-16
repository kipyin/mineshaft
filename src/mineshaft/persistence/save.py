from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from mineshaft.domain.dimension import Dimension
from mineshaft.domain.direction import Direction
from mineshaft.domain.end_run import EndRun
from mineshaft.domain.inventory import Inventory
from mineshaft.domain.mc_game_mode import MCGameMode
from mineshaft.domain.mineshaft_run import MineshaftRoom, MineshaftRun
from mineshaft.domain.overworld import Overworld, OverworldMob, first_walkable_inner_tile
from mineshaft.domain.player import Player
from mineshaft.domain.pos import Pos
from mineshaft.domain.tiles import BiomeKind, Tile, TileKind
from mineshaft.sim.engine import Game

SCHEMA_VERSION = 4


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
        fixed = dict(rr)
        fixed.setdefault("exit_to_end_portal", False)
        rooms[rid] = MineshaftRoom(**fixed)
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


def _normalize_mc_game_mode(raw: object) -> MCGameMode:
    if raw in ("survival", "creative", "adventure", "spectator"):
        return raw  # type: ignore[return-value]
    return "survival"


def _infer_dimension(raw: dict[str, Any]) -> Dimension:
    if "dimension" in raw:
        d = raw["dimension"]
        if d in ("overworld", "dungeon", "nether", "end"):
            return d  # type: ignore[return-value]
    # Legacy: `mode` held world layer; "nether" was the mineshaft crawl in v2–v3.
    m = raw.get("mode", "overworld")
    if m == "end":
        return "end"
    if m in ("mineshaft", "dungeon"):
        return "dungeon"
    if m == "nether":
        return "dungeon"
    if m == "overworld":
        return "overworld"
    return "overworld"


def _serialize_end_run(er: EndRun) -> dict[str, Any]:
    return {
        "dragon_hp": er.dragon_hp,
        "dragon_max_hp": er.dragon_max_hp,
        "phase": er.phase,
    }


def _deserialize_end_run(d: dict[str, Any]) -> EndRun:
    return EndRun(
        dragon_hp=int(d["dragon_hp"]),
        dragon_max_hp=int(d["dragon_max_hp"]),
        phase=int(d.get("phase", 0)),
    )


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
        "dimension": game.dimension,
        "mc_game_mode": game.mc_game_mode,
        "overworld": _serialize_overworld(game.overworld),
        "nether_world": _serialize_overworld(game.nether_world)
        if game.nether_world
        else None,
        "end_world": _serialize_overworld(game.end_world) if game.end_world else None,
        "player": _serialize_player(game.player),
        "spawn_pos": [game.spawn_pos.x, game.spawn_pos.y],
        "mineshaft_runs": {k: _serialize_mineshaft_run(v) for k, v in game.mineshaft_runs.items()},
        "active_mineshaft_id": game.mineshaft_run.mineshaft_id if game.mineshaft_run else None,
        "saved_entrance_facing": game.saved_entrance_facing.name,
        "overworld_nether_portal_pos": [
            game.overworld_nether_portal_pos.x,
            game.overworld_nether_portal_pos.y,
        ],
        "nether_spawn_pos": [game.nether_spawn_pos.x, game.nether_spawn_pos.y]
        if game.nether_spawn_pos
        else None,
        "end_dragon_pos": [game.end_dragon_pos.x, game.end_dragon_pos.y]
        if game.end_dragon_pos
        else None,
        "end_entry_spawn": [game.end_entry_spawn.x, game.end_entry_spawn.y]
        if game.end_entry_spawn
        else None,
        "moves_since_hunger": game.moves_since_hunger,
        "world_time_ticks": game.world_time_ticks,
        "log": game.log_lines,
        "victory": game.victory,
        "end_run": _serialize_end_run(game.end_run) if game.end_run else None,
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
    dimension = _infer_dimension(raw)
    mc_game_mode = _normalize_mc_game_mode(raw.get("mc_game_mode", "survival"))

    nether_world: Overworld | None = None
    if raw.get("nether_world"):
        nether_world = _deserialize_overworld(raw["nether_world"])
    end_world: Overworld | None = None
    if raw.get("end_world"):
        end_world = _deserialize_overworld(raw["end_world"])

    if raw.get("overworld_nether_portal_pos"):
        ox, oy = raw["overworld_nether_portal_pos"]
        overworld_nether_portal_pos = Pos(int(ox), int(oy))
    else:
        overworld_nether_portal_pos = _scan_portal(ow)

    nether_spawn_pos: Pos | None = None
    if raw.get("nether_spawn_pos"):
        nx, ny = raw["nether_spawn_pos"]
        nether_spawn_pos = Pos(int(nx), int(ny))
    elif nether_world:
        nether_spawn_pos = _scan_nether_spawn_beside_portal(nether_world)

    end_dragon_pos: Pos | None = None
    if raw.get("end_dragon_pos"):
        dx, dy = raw["end_dragon_pos"]
        end_dragon_pos = Pos(int(dx), int(dy))
    elif end_world:
        end_dragon_pos = Pos(end_world.width // 2, end_world.height // 2)

    end_entry_spawn: Pos | None = None
    if raw.get("end_entry_spawn"):
        ex, ey = raw["end_entry_spawn"]
        end_entry_spawn = Pos(int(ex), int(ey))
    elif end_world:
        end_entry_spawn = first_walkable_inner_tile(end_world)

    end_raw = raw.get("end_run")
    end_run: EndRun | None = _deserialize_end_run(end_raw) if end_raw else None
    victory = bool(raw.get("victory", False))
    if dimension == "end" and end_run is None:
        dimension = "overworld"
        victory = False
    if dimension == "nether" and nether_world is None:
        dimension = "overworld"
    if dimension == "end" and end_world is None:
        dimension = "overworld"
        end_run = None
        victory = False

    g = Game.from_snapshot(
        seed=raw["seed"],
        overworld=ow,
        player=player,
        spawn_pos=spawn_pos,
        dimension=dimension,
        mc_game_mode=mc_game_mode,
        mineshaft_runs=mineshaft_runs,
        mineshaft_run=active,
        saved_entrance_facing=Direction[raw["saved_entrance_facing"]],
        overworld_nether_portal_pos=overworld_nether_portal_pos,
        nether_spawn_pos=nether_spawn_pos,
        nether_world=nether_world,
        end_world=end_world,
        end_dragon_pos=end_dragon_pos,
        end_entry_spawn=end_entry_spawn,
        moves_since_hunger=raw.get("moves_since_hunger", 0),
        world_time_ticks=raw.get("world_time_ticks", 0),
        log=list(raw.get("log", [])),
        end_run=end_run,
        victory=victory,
    )
    if g.player.hp <= 0:
        g.player.hp = g.player.max_hp
        g.player.hunger = g.player.max_hunger
        if g.dimension in ("dungeon", "nether", "end"):
            g.dimension = "overworld"
            g.mineshaft_run = None
            g.end_run = None
            g.victory = False
            g.nether_world = None
            g.end_world = None
            g.end_dragon_pos = None
            g.end_entry_spawn = None
        g.player.pos = Pos(g.spawn_pos.x, g.spawn_pos.y)
    return g


def _scan_portal(ow: Overworld) -> Pos:
    for y in range(ow.height):
        for x in range(ow.width):
            if ow.tile_at(Pos(x, y)).kind is TileKind.NETHER_PORTAL:
                return Pos(x, y)
    return Pos(ow.width // 2, ow.height // 2)


def _scan_nether_spawn_beside_portal(nw: Overworld) -> Pos:
    for y in range(nw.height):
        for x in range(nw.width):
            if nw.tile_at(Pos(x, y)).kind is TileKind.NETHER_PORTAL:
                for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    np = Pos(x + dx, y + dy)
                    if nw.in_bounds(np) and not nw.tile_at(np).blocks_movement():
                        return np
                return Pos(x, y)
    return first_walkable_inner_tile(nw)
