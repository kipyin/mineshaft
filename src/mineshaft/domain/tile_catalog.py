from __future__ import annotations

import importlib.resources
import os
import tomllib
from pathlib import Path
from typing import Any

import yaml
from rich.style import Style

DEFAULT_STYLE = "white on bright_black"
DEFAULT_CHAR = "█"

ParsedTileRules = tuple[frozenset[str], frozenset[str], dict[str, str], dict[str, str]]
LoadedTileCatalog = tuple[frozenset[str], frozenset[str], dict[str, Style], dict[str, str]]


def resolve_tiles_path(cwd: Path | None = None) -> Path | None:
    env = os.environ.get("MINESHAFT_TILES", "").strip()
    if env:
        p = Path(env).expanduser()
        if not p.is_file():
            raise FileNotFoundError(f"MINESHAFT_TILES does not point to a file: {p}")
        return p

    base = cwd or Path.cwd()
    for name in ("mineshaft_tiles.toml", "mineshaft_tiles.yaml", "mineshaft_tiles.yml"):
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
        raise ValueError(f"Tiles catalog root must be a mapping: {path}")
    return data


def load_bundled_tiles_dict() -> dict[str, Any]:
    ref = importlib.resources.files("mineshaft.data").joinpath("tiles.toml")
    with ref.open("rb") as f:
        return tomllib.load(f)


def load_tiles_dict(path: Path | None = None) -> dict[str, Any]:
    if path is None:
        return load_bundled_tiles_dict()
    return _load_document(path)


def parse_tiles_dict(data: dict[str, Any]) -> ParsedTileRules:
    rules = data.get("rules", {})
    if not isinstance(rules, dict):
        raise ValueError("tiles: rules must be a table")
    bm = rules.get("blocks_movement", [])
    nm = rules.get("not_mineable", [])
    if not isinstance(bm, list) or not all(isinstance(x, str) for x in bm):
        raise ValueError("tiles: rules.blocks_movement must be a list of strings")
    if not isinstance(nm, list) or not all(isinstance(x, str) for x in nm):
        raise ValueError("tiles: rules.not_mineable must be a list of strings")

    styles: dict[str, str] = {}
    chars: dict[str, str] = {}
    tile_render = data.get("tile_render", {})
    if not isinstance(tile_render, dict):
        raise ValueError("tiles: tile_render must be a table")
    for tile_id, section in tile_render.items():
        if not isinstance(section, dict):
            raise ValueError(f"tiles: tile_render.{tile_id} must be a table")
        if "style" not in section or "char" not in section:
            raise ValueError(f"tiles: tile_render.{tile_id} needs style and char")
        styles[str(tile_id)] = str(section["style"])
        chars[str(tile_id)] = str(section["char"])

    return frozenset(bm), frozenset(nm), styles, chars


def _build_style_map(style_strings: dict[str, str]) -> dict[str, Style]:
    return {k: Style.parse(v) for k, v in style_strings.items()}


def load_tile_catalog(path: Path | None = None) -> LoadedTileCatalog:
    if path is not None:
        data = load_tiles_dict(path)
    else:
        resolved = resolve_tiles_path()
        data = load_tiles_dict(resolved)
    bm, nm, st, ch = parse_tiles_dict(data)
    return bm, nm, _build_style_map(st), ch


BLOCKS_MOVEMENT: frozenset[str]
NOT_MINEABLE: frozenset[str]
_TILE_STYLES: dict[str, Style]
_TILE_CHARS: dict[str, str]

BLOCKS_MOVEMENT, NOT_MINEABLE, _TILE_STYLES, _TILE_CHARS = load_tile_catalog()


def tile_style(tile_id: str) -> Style:
    return _TILE_STYLES.get(tile_id, Style.parse(DEFAULT_STYLE))


def tile_char(tile_id: str) -> str:
    return _TILE_CHARS.get(tile_id, DEFAULT_CHAR)


def reload_tile_catalog(path: Path | None = None) -> None:
    global BLOCKS_MOVEMENT, NOT_MINEABLE, _TILE_STYLES, _TILE_CHARS
    bm, nm, st, ch = load_tile_catalog(path)
    BLOCKS_MOVEMENT = bm
    NOT_MINEABLE = nm
    _TILE_STYLES = st
    _TILE_CHARS = ch
