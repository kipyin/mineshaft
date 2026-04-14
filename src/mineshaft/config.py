from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Runtime options; env overrides file."""

    keep_inventory_on_respawn: bool


def load_settings(base_path: Path | None = None) -> Settings:
    env = os.environ.get("MINESHAFT_KEEP_INVENTORY", "").strip().lower()
    if env in ("1", "true", "yes", "on"):
        return Settings(keep_inventory_on_respawn=True)
    if env in ("0", "false", "no", "off"):
        return Settings(keep_inventory_on_respawn=False)

    path = (base_path or Path.cwd()) / "mineshaft_settings.json"
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            ki = bool(data.get("keep_inventory_on_respawn", False))
            return Settings(keep_inventory_on_respawn=ki)
        except (json.JSONDecodeError, OSError):
            pass
    return Settings(keep_inventory_on_respawn=False)
