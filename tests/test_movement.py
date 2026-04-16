"""Facing-gated movement: first key turns; same direction again steps."""

from __future__ import annotations

from mineshaft.domain.direction import Direction
from mineshaft.domain.overworld import Overworld
from mineshaft.domain.player import Player
from mineshaft.domain.pos import Pos
from mineshaft.domain.tiles import BiomeKind, Tile, TileKind
from mineshaft.sim.engine import Game


def _tiny_grass_overworld() -> Overworld:
    w, h = 5, 5
    grass = Tile(TileKind.GRASS)
    tiles = [[grass for _ in range(w)] for _ in range(h)]
    biome = [[BiomeKind.PLAINS for _ in range(w)] for _ in range(h)]
    return Overworld(width=w, height=h, tiles=tiles, biome=biome, cave_to_mineshaft_id={}, mobs={})


def _minimal_snapshot(
    *,
    overworld: Overworld,
    player: Player,
    spawn_pos: Pos,
) -> Game:
    return Game.from_snapshot(
        seed=99,
        overworld=overworld,
        player=player,
        spawn_pos=spawn_pos,
        dimension="overworld",
        mc_game_mode="survival",
        mineshaft_runs={},
        mineshaft_run=None,
        saved_entrance_facing=Direction.N,
        overworld_nether_portal_pos=spawn_pos,
        nether_spawn_pos=None,
        nether_world=None,
        end_world=None,
        end_dragon_pos=None,
        end_entry_spawn=None,
        moves_since_hunger=0,
        world_time_ticks=1000,
        log=[],
    )


def test_overworld_first_key_turns_without_move_or_hunger_tick() -> None:
    ow = _tiny_grass_overworld()
    pos = Pos(2, 2)
    p = Player(pos=pos, facing=Direction.N)
    g = _minimal_snapshot(overworld=ow, player=p, spawn_pos=pos)
    wt0 = g.world_time_ticks
    ms0 = g.moves_since_hunger
    g.move_topdown("E")
    assert p.pos == pos
    assert p.facing == Direction.E
    assert g.world_time_ticks == wt0
    assert g.moves_since_hunger == ms0


def test_overworld_second_key_in_same_direction_moves() -> None:
    ow = _tiny_grass_overworld()
    pos = Pos(2, 2)
    p = Player(pos=pos, facing=Direction.N)
    g = _minimal_snapshot(overworld=ow, player=p, spawn_pos=pos)
    g.world_time_ticks = 0
    g.move_topdown("E")
    g.move_topdown("E")
    assert p.pos == Pos(3, 2)
    assert p.facing == Direction.E
