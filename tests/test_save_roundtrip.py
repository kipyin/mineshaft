from __future__ import annotations

from pathlib import Path

from mineshaft.persistence.save import load_game, save_game
from mineshaft.sim.engine import Game


def test_save_roundtrip(tmp_path: Path) -> None:
    g1 = Game(seed=4242)
    g1.player.inventory.add("stick", 3)
    p = tmp_path / "s.json"
    save_game(p, g1)
    g2 = load_game(p)
    assert g2.seed == g1.seed
    assert g2.player.inventory.count("stick") == 3
    assert g2.mode == g1.mode
