from pathlib import Path

import pytest

from mineshaft.config import Settings, load_settings, save_settings


def test_save_settings_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MINESHAFT_KEEP_INVENTORY", raising=False)
    s = Settings(
        keep_inventory_on_respawn=True,
        max_viewport_radius_w=30,
        max_viewport_radius_h=15,
    )
    save_settings(s, base_path=tmp_path)
    loaded = load_settings(base_path=tmp_path)
    assert loaded.keep_inventory_on_respawn is True
    assert loaded.max_viewport_radius_w == 30
    assert loaded.max_viewport_radius_h == 15
