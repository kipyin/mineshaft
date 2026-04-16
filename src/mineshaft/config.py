from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Runtime options; env overrides file."""

    keep_inventory_on_respawn: bool
    # Upper bounds for overworld map half-size (cells from player to edge).
    # Large terminals otherwise build huge Rich Text buffers each frame.
    max_viewport_radius_w: int
    max_viewport_radius_h: int


def _clamp_viewport_w(n: int) -> int:
    return max(1, min(100, n))


def _clamp_viewport_h(n: int) -> int:
    return max(1, min(50, n))


def _viewport_from_settings_data(data: dict | None) -> tuple[int, int]:
    default_rw, default_rh = 40, 22
    if data is None:
        return default_rw, default_rh
    rw = _clamp_viewport_w(int(data.get("max_viewport_radius_w", default_rw)))
    rh = _clamp_viewport_h(int(data.get("max_viewport_radius_h", default_rh)))
    return rw, rh


def load_settings(base_path: Path | None = None) -> Settings:
    path = (base_path or Path.cwd()) / "mineshaft_settings.json"
    data: dict | None = None
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = None

    rw, rh = _viewport_from_settings_data(data)

    env = os.environ.get("MINESHAFT_KEEP_INVENTORY", "").strip().lower()
    if env in ("1", "true", "yes", "on"):
        return Settings(
            keep_inventory_on_respawn=True,
            max_viewport_radius_w=rw,
            max_viewport_radius_h=rh,
        )
    if env in ("0", "false", "no", "off"):
        return Settings(
            keep_inventory_on_respawn=False,
            max_viewport_radius_w=rw,
            max_viewport_radius_h=rh,
        )

    if data is not None:
        ki = bool(data.get("keep_inventory_on_respawn", False))
    else:
        ki = False

    return Settings(
        keep_inventory_on_respawn=ki,
        max_viewport_radius_w=rw,
        max_viewport_radius_h=rh,
    )


def save_settings(settings: Settings, base_path: Path | None = None) -> None:
    """Write settings to mineshaft_settings.json (env vars still override on load)."""
    path = (base_path or Path.cwd()) / "mineshaft_settings.json"
    data = {
        "keep_inventory_on_respawn": settings.keep_inventory_on_respawn,
        "max_viewport_radius_w": settings.max_viewport_radius_w,
        "max_viewport_radius_h": settings.max_viewport_radius_h,
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
