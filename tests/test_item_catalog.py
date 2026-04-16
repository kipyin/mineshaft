from __future__ import annotations

from pathlib import Path

import pytest

from mineshaft.domain import items as items_mod
from mineshaft.domain.item_catalog import (
    load_bundled_catalog_dict,
    parse_catalog_dict,
    resolve_catalog_path,
)
from mineshaft.domain.items import reload_item_catalog


def test_parse_catalog_minimal() -> None:
    data = {
        "display_names": {"stick": "Stick"},
        "recipes": [{"produces": "plank", "count": 4, "needs": {"wood": 1}}],
    }
    display, rows = parse_catalog_dict(data)
    assert display == {"stick": "Stick"}
    assert rows == [({"wood": 1}, "plank", 4)]


def test_parse_rejects_bad_needs() -> None:
    with pytest.raises(ValueError, match="needs must be"):
        parse_catalog_dict(
            {"recipes": [{"produces": "x", "needs": "nope"}]},
        )


def test_bundled_catalog_has_recipes() -> None:
    data = load_bundled_catalog_dict()
    display, rows = parse_catalog_dict(data)
    assert "stick" in display
    assert len(rows) >= 12


def test_reload_from_temp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p = tmp_path / "items.toml"
    p.write_text(
        "\n".join(
            [
                '[display_names]',
                'stick = "Stick"',
                '[[recipes]]',
                'produces = "plank"',
                'count = 1',
                'needs = { wood = 1 }',
                "",
            ]
        ),
        encoding="utf-8",
    )
    try:
        reload_item_catalog(p)
        assert len(items_mod.RECIPES) == 1
        assert items_mod.RECIPES[0].produces == "plank"
    finally:
        monkeypatch.chdir(tmp_path)
        reload_item_catalog()


def test_resolve_catalog_prefers_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    p = tmp_path / "custom.toml"
    p.write_text(
        '[display_names]\nstick = "S"\nrecipes = []\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("MINESHAFT_ITEMS", str(p))
    assert resolve_catalog_path() == p


def test_resolve_catalog_cwd_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "mineshaft_items.toml").write_text(
        '[display_names]\nstick = "S"\nrecipes = []\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    assert resolve_catalog_path() == tmp_path / "mineshaft_items.toml"
