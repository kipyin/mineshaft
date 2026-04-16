from __future__ import annotations

import importlib.resources
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True, slots=True)
class MobSpawnLoop:
    """Repeated random placement attempts (overworld / nether initial mobs)."""

    attempts: int
    chance: float
    kinds: tuple[str, ...]
    hp_min: int
    hp_max: int
    atk_min: int
    atk_max: int


@dataclass(frozen=True, slots=True)
class MobRandomEncounter:
    """Single-roll encounter when entering a forest cell (overworld)."""

    chance: float
    kinds: tuple[str, ...]
    hp_min: int
    hp_max: int
    atk_min: int
    atk_max: int


@dataclass(frozen=True, slots=True)
class MobCatalogData:
    overworld_static: MobSpawnLoop
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


def _spawn_loop(d: dict[str, Any], *, section: str) -> MobSpawnLoop:
    try:
        return MobSpawnLoop(
            attempts=int(d["attempts"]),
            chance=float(d["chance"]),
            kinds=tuple(str(x) for x in d["kinds"]),
            hp_min=int(d["hp_min"]),
            hp_max=int(d["hp_max"]),
            atk_min=int(d["atk_min"]),
            atk_max=int(d["atk_max"]),
        )
    except KeyError as e:
        raise ValueError(f"mobs: {section} missing field: {e}") from e


def _random_encounter(d: dict[str, Any], *, section: str) -> MobRandomEncounter:
    try:
        return MobRandomEncounter(
            chance=float(d["chance"]),
            kinds=tuple(str(x) for x in d["kinds"]),
            hp_min=int(d["hp_min"]),
            hp_max=int(d["hp_max"]),
            atk_min=int(d["atk_min"]),
            atk_max=int(d["atk_max"]),
        )
    except KeyError as e:
        raise ValueError(f"mobs: {section} missing field: {e}") from e


def parse_mobs_dict(data: dict[str, Any]) -> MobCatalogData:
    ow = data.get("overworld", {})
    ne = data.get("nether", {})
    ms = data.get("mineshaft", {})
    if not isinstance(ow, dict) or not isinstance(ne, dict) or not isinstance(ms, dict):
        raise ValueError("mobs: overworld, nether, mineshaft must be tables")

    static = ow.get("static_spawns", {})
    enc = ow.get("random_encounter", {})
    nstatic = ne.get("static_spawns", {})
    if not isinstance(static, dict) or not isinstance(enc, dict) or not isinstance(nstatic, dict):
        raise ValueError("mobs: overworld/nether spawn sections must be tables")

    pool = ms.get("room_mob_pool", [])
    if not isinstance(pool, list) or not all(isinstance(x, str) for x in pool):
        raise ValueError("mobs: mineshaft.room_mob_pool must be a list of strings")

    return MobCatalogData(
        overworld_static=_spawn_loop(static, section="overworld.static_spawns"),
        overworld_encounter=_random_encounter(enc, section="overworld.random_encounter"),
        nether_static=_spawn_loop(nstatic, section="nether.static_spawns"),
        mineshaft_pool=tuple(pool),
    )


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
