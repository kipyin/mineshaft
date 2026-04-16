from __future__ import annotations

import importlib.resources
import os
import tomllib
from pathlib import Path
from typing import Any

import yaml

RecipeRow = tuple[dict[str, int], str, int]


def resolve_catalog_path(cwd: Path | None = None) -> Path | None:
    """Return a user override path, or None to use the bundled default."""
    env = os.environ.get("MINESHAFT_ITEMS", "").strip()
    if env:
        p = Path(env).expanduser()
        if not p.is_file():
            raise FileNotFoundError(f"MINESHAFT_ITEMS does not point to a file: {p}")
        return p

    base = cwd or Path.cwd()
    for name in ("mineshaft_items.toml", "mineshaft_items.yaml", "mineshaft_items.yml"):
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
        raise ValueError(f"Catalog root must be a mapping: {path}")
    return data


def load_bundled_catalog_dict() -> dict[str, Any]:
    ref = importlib.resources.files("mineshaft.data").joinpath("items.toml")
    with ref.open("rb") as f:
        return tomllib.load(f)


def load_catalog_dict(path: Path | None = None) -> dict[str, Any]:
    """Load items + recipes from TOML or YAML. Uses bundled defaults when path is None."""
    if path is None:
        return load_bundled_catalog_dict()
    return _load_document(path)


def parse_catalog_dict(data: dict[str, Any]) -> tuple[dict[str, str], list[RecipeRow]]:
    """Validate catalog shape: display_names + recipes with shapeless needs."""
    raw_display = data.get("display_names", {})
    if not isinstance(raw_display, dict):
        raise ValueError("display_names must be a table/mapping")
    display_names = {str(k): str(v) for k, v in raw_display.items()}

    raw_recs = data.get("recipes", [])
    if not isinstance(raw_recs, list):
        raise ValueError("recipes must be a list")
    recipes: list[RecipeRow] = []
    for i, rec in enumerate(raw_recs):
        if not isinstance(rec, dict):
            raise ValueError(f"recipes[{i}] must be a table/mapping")
        try:
            produces = str(rec["produces"])
        except KeyError as e:
            raise ValueError(f"recipes[{i}] missing produces") from e
        count = int(rec.get("count", 1))
        needs_raw = rec.get("needs", {})
        if not isinstance(needs_raw, dict):
            raise ValueError(f"recipes[{i}] needs must be a table/mapping")
        needs = {str(k): int(v) for k, v in needs_raw.items()}
        recipes.append((needs, produces, count))

    return display_names, recipes
