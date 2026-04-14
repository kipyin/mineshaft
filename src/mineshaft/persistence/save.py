from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from mineshaft.domain.direction import Direction
from mineshaft.domain.dungeon import DungeonInstance, DungeonRoom
from mineshaft.domain.inventory import Inventory
from mineshaft.domain.overworld import Overworld, OverworldMob
from mineshaft.domain.player import Player
from mineshaft.domain.pos import Pos
from mineshaft.domain.tiles import BiomeKind, Tile, TileKind
from mineshaft.sim.engine import Game

SCHEMA_VERSION = 1


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
        "cave_to_dungeon": {f"{x},{y}": v for (x, y), v in ow.cave_to_dungeon.items()},
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
    cave_raw = d["cave_to_dungeon"]
    cave_to_dungeon: dict[tuple[int, int], str] = {}
    for k, v in cave_raw.items():
        xs, ys = k.split(",")
        cave_to_dungeon[(int(xs), int(ys))] = v
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
        cave_to_dungeon=cave_to_dungeon,
        mobs=mobs,
    )


def _serialize_dungeon(di: DungeonInstance) -> dict[str, Any]:
    rooms = {k: asdict(v) for k, v in di.rooms.items()}
    return {
        "dungeon_id": di.dungeon_id,
        "tier": di.tier,
        "rooms": rooms,
        "current_room": di.current_room,
        "entrance_room_id": di.entrance_room_id,
        "overworld_return": list(di.overworld_return),
    }


def _deserialize_dungeon(d: dict[str, Any]) -> DungeonInstance:
    rooms_raw = d["rooms"]
    rooms: dict[str, DungeonRoom] = {}
    for rid, rr in rooms_raw.items():
        rooms[rid] = DungeonRoom(**rr)
    ox, oy = d["overworld_return"]
    return DungeonInstance(
        dungeon_id=d["dungeon_id"],
        tier=d["tier"],
        rooms=rooms,
        current_room=d["current_room"],
        entrance_room_id=d["entrance_room_id"],
        overworld_return=(int(ox), int(oy)),
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
        "mode": game.mode,
        "overworld": _serialize_overworld(game.overworld),
        "player": _serialize_player(game.player),
        "dungeons": {k: _serialize_dungeon(v) for k, v in game.dungeons.items()},
        "active_dungeon_id": game.dungeon.dungeon_id if game.dungeon else None,
        "saved_entrance_facing": game.saved_entrance_facing.name,
        "moves_since_hunger": game.moves_since_hunger,
        "log": game.log_lines,
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_game(path: Path) -> Game:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version", 1) != SCHEMA_VERSION:
        raise ValueError("Unsupported save schema")

    ow = _deserialize_overworld(raw["overworld"])
    player = _deserialize_player(raw["player"])
    dungeons = {k: _deserialize_dungeon(v) for k, v in raw["dungeons"].items()}
    aid = raw.get("active_dungeon_id")
    dung = dungeons[aid] if aid else None
    return Game.from_snapshot(
        seed=raw["seed"],
        overworld=ow,
        player=player,
        mode=raw["mode"],
        dungeons=dungeons,
        dungeon=dung,
        saved_entrance_facing=Direction[raw["saved_entrance_facing"]],
        moves_since_hunger=raw.get("moves_since_hunger", 0),
        log=list(raw.get("log", [])),
    )
