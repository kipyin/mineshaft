from __future__ import annotations

import importlib.resources
import os
import random
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from mineshaft.domain.inventory import Inventory
from mineshaft.domain.items import ItemId
from mineshaft.domain.overworld import OverworldMob


def _known_item_ids() -> frozenset[str]:
    return frozenset(
        v for k, v in vars(ItemId).items() if not k.startswith("_") and isinstance(v, str)
    )


@dataclass(frozen=True, slots=True)
class MobDrop:
    item: str
    chance: float
    count_min: int
    count_max: int


@dataclass(frozen=True, slots=True)
class MobDefinition:
    kind_id: str
    hp: int
    atk: int
    hostile: bool
    drops: tuple[MobDrop, ...]


@dataclass(frozen=True, slots=True)
class MobSpawnLoop:
    """Repeated random placement attempts (overworld / nether initial mobs)."""

    attempts: int
    chance: float
    kinds: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MobRandomEncounter:
    """Single-roll encounter when entering a forest cell (overworld)."""

    chance: float
    kinds: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MobCatalogData:
    definitions: dict[str, MobDefinition]
    boss_ender_dragon_hp: int
    overworld_static_forest: MobSpawnLoop
    overworld_static_plains: MobSpawnLoop
    overworld_encounter: MobRandomEncounter
    nether_static: MobSpawnLoop
    mineshaft_pool: tuple[str, ...]


def resolve_mobs_path(cwd: Path | None = None) -> Path | None:
    env = os.environ.get("MINESHAFT_MOBS", "").strip()
    if env:
        p = Path(env).expanduser()
        if not p.is_file():
            raise FileNotFoundError(f"MINESHAFT_MOBS does not point to a file: {p}")
        return p

    base = cwd or Path.cwd()
    for name in ("mineshaft_mobs.toml", "mineshaft_mobs.yaml", "mineshaft_mobs.yml"):
        candidate = base / name
        if candidate.is_file():
            return candidate
    return None


def _load_document(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        data = yaml.safe_load(raw.decode("utf-8"))
    else:
        data = tomllib.loads(raw.decode("utf-8"))
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"Mobs catalog root must be a mapping: {path}")
    return data


def load_bundled_mobs_dict() -> dict[str, Any]:
    ref = importlib.resources.files("mineshaft.data").joinpath("mobs.toml")
    with ref.open("rb") as f:
        return tomllib.load(f)


def load_mobs_dict(path: Path | None = None) -> dict[str, Any]:
    if path is None:
        return load_bundled_mobs_dict()
    return _load_document(path)


def _parse_drop(raw: dict[str, Any], *, mob_id: str, index: int) -> MobDrop:
    try:
        item = str(raw["item"])
        chance = float(raw["chance"])
    except KeyError as e:
        raise ValueError(f"mobs: definitions.{mob_id}.drops[{index}] missing {e}") from e
    known = _known_item_ids()
    if item not in known:
        raise ValueError(f"mobs: definitions.{mob_id} drop item unknown: {item!r}")
    if "count" in raw:
        c = int(raw["count"])
        count_min = count_max = c
    else:
        count_min = int(raw["count_min"])
        count_max = int(raw["count_max"])
    return MobDrop(item=item, chance=chance, count_min=count_min, count_max=count_max)


def _parse_mob_definition(mob_id: str, raw: dict[str, Any]) -> MobDefinition:
    try:
        hp = int(raw["hp"])
        atk = int(raw["atk"])
    except KeyError as e:
        raise ValueError(f"mobs: definitions.{mob_id} missing {e}") from e
    hostile = bool(raw.get("hostile", True))
    drops_raw = raw.get("drops", [])
    if drops_raw is None:
        drops_raw = []
    if not isinstance(drops_raw, list):
        raise ValueError(f"mobs: definitions.{mob_id}.drops must be a list")
    drops = tuple(_parse_drop(d, mob_id=mob_id, index=i) for i, d in enumerate(drops_raw))
    return MobDefinition(kind_id=mob_id, hp=hp, atk=atk, hostile=hostile, drops=drops)


def parse_definitions(data: dict[str, Any]) -> dict[str, MobDefinition]:
    defs_raw = data.get("definitions", {})
    if not isinstance(defs_raw, dict):
        raise ValueError("mobs: definitions must be a table")
    out: dict[str, MobDefinition] = {}
    for mob_id, raw in defs_raw.items():
        if not isinstance(raw, dict):
            raise ValueError(f"mobs: definitions.{mob_id} must be a table")
        mid = str(mob_id)
        out[mid] = _parse_mob_definition(mid, raw)
    return out


def _spawn_loop(d: dict[str, Any], *, section: str) -> MobSpawnLoop:
    try:
        return MobSpawnLoop(
            attempts=int(d["attempts"]),
            chance=float(d["chance"]),
            kinds=tuple(str(x) for x in d["kinds"]),
        )
    except KeyError as e:
        raise ValueError(f"mobs: {section} missing field: {e}") from e


def _random_encounter(d: dict[str, Any], *, section: str) -> MobRandomEncounter:
    try:
        return MobRandomEncounter(
            chance=float(d["chance"]),
            kinds=tuple(str(x) for x in d["kinds"]),
        )
    except KeyError as e:
        raise ValueError(f"mobs: {section} missing field: {e}") from e


def _assert_kinds_in_definitions(
    definitions: dict[str, MobDefinition],
    kinds: tuple[str, ...],
    *,
    context: str,
) -> None:
    for k in kinds:
        if k not in definitions:
            raise ValueError(f"mobs: {context} references unknown mob kind {k!r}")


def parse_mobs_dict(data: dict[str, Any]) -> MobCatalogData:
    definitions = parse_definitions(data)

    ow = data.get("overworld", {})
    ne = data.get("nether", {})
    ms = data.get("mineshaft", {})
    boss = data.get("boss", {})
    if not isinstance(ow, dict) or not isinstance(ne, dict) or not isinstance(ms, dict):
        raise ValueError("mobs: overworld, nether, mineshaft must be tables")
    if not isinstance(boss, dict):
        raise ValueError("mobs: boss must be a table")

    forest = ow.get("static_spawns_forest", {})
    plains = ow.get("static_spawns_plains", {})
    enc = ow.get("random_encounter", {})
    nstatic = ne.get("static_spawns", {})
    if not isinstance(forest, dict) or not isinstance(plains, dict):
        raise ValueError("mobs: overworld static spawn sections must be tables")
    if not isinstance(enc, dict) or not isinstance(nstatic, dict):
        raise ValueError("mobs: overworld/nether encounter sections must be tables")

    pool = ms.get("room_mob_pool", [])
    if not isinstance(pool, list) or not all(isinstance(x, str) for x in pool):
        raise ValueError("mobs: mineshaft.room_mob_pool must be a list of strings")

    ed_raw = boss.get("ender_dragon", {})
    if not isinstance(ed_raw, dict):
        raise ValueError("mobs: boss.ender_dragon must be a table")
    try:
        boss_ender_dragon_hp = int(ed_raw["hp"])
    except KeyError as e:
        raise ValueError("mobs: boss.ender_dragon missing hp") from e

    sf = _spawn_loop(forest, section="overworld.static_spawns_forest")
    sp = _spawn_loop(plains, section="overworld.static_spawns_plains")
    en = _random_encounter(enc, section="overworld.random_encounter")
    ns = _spawn_loop(nstatic, section="nether.static_spawns")
    mp = tuple(pool)

    for ctx, kinds in (
        ("overworld.static_spawns_forest", sf.kinds),
        ("overworld.static_spawns_plains", sp.kinds),
        ("overworld.random_encounter", en.kinds),
        ("nether.static_spawns", ns.kinds),
        ("mineshaft.room_mob_pool", mp),
    ):
        _assert_kinds_in_definitions(definitions, kinds, context=ctx)

    return MobCatalogData(
        definitions=definitions,
        boss_ender_dragon_hp=boss_ender_dragon_hp,
        overworld_static_forest=sf,
        overworld_static_plains=sp,
        overworld_encounter=en,
        nether_static=ns,
        mineshaft_pool=mp,
    )


def instantiate_mob(kind: str, definitions: dict[str, MobDefinition]) -> OverworldMob:
    d = definitions[kind]
    atk = 0 if not d.hostile else d.atk
    return OverworldMob(kind=kind, hp=d.hp, max_hp=d.hp, atk=atk)


def mob_definition(kind: str, definitions: dict[str, MobDefinition]) -> MobDefinition | None:
    return definitions.get(kind)


def roll_drop_quantity(rng: random.Random, drop: MobDrop) -> int:
    if drop.count_min == drop.count_max:
        return drop.count_min
    return rng.randint(drop.count_min, drop.count_max)


def apply_mob_drops(
    rng: random.Random,
    inv: Inventory,
    definition: MobDefinition,
) -> list[tuple[str, int]]:
    """Roll drops from ``definition`` into ``inv``. Returns (item, count) for logging."""
    gained: list[tuple[str, int]] = []
    for drop in definition.drops:
        if rng.random() >= drop.chance:
            continue
        n = roll_drop_quantity(rng, drop)
        if n <= 0:
            continue
        inv.add(drop.item, n)
        gained.append((drop.item, n))
    return gained


def load_mob_catalog(path: Path | None = None) -> MobCatalogData:
    if path is not None:
        data = load_mobs_dict(path)
    else:
        resolved = resolve_mobs_path()
        data = load_mobs_dict(resolved)
    return parse_mobs_dict(data)


MOBS: MobCatalogData = load_mob_catalog()


def reload_mob_catalog(path: Path | None = None) -> None:
    global MOBS
    MOBS = load_mob_catalog(path)
