from __future__ import annotations

import random
from typing import Literal

from mineshaft.config import load_settings
from mineshaft.domain import items as items_mod
from mineshaft.domain import mob_catalog as mob_catalog_mod
from mineshaft.domain.dimension import Dimension
from mineshaft.domain.direction import Direction
from mineshaft.domain.end_run import EndRun
from mineshaft.domain.items import ItemId
from mineshaft.domain.mc_game_mode import MCGameMode
from mineshaft.domain.mineshaft_run import MineshaftRun
from mineshaft.domain.overworld import Overworld, OverworldMob
from mineshaft.domain.player import Player
from mineshaft.domain.pos import Pos
from mineshaft.domain.tiles import BiomeKind, TileKind
from mineshaft.gen.end_gen import generate_end_world
from mineshaft.gen.mineshaft_gen import generate_mineshaft
from mineshaft.gen.nether_gen import generate_nether_world
from mineshaft.gen.overworld_gen import generate_overworld
from mineshaft.sim.combat import (
    DRAGON_MAX_HP,
    nether_player_damage,
    resolve_end_dragon_exchange,
    resolve_overworld_melee,
)
from mineshaft.sim.crafting import try_craft
from mineshaft.sim.mining import can_mine_tile, mine_tile

MoveDir = Literal["N", "S", "E", "W"]
MAX_LOG = 80
WORLD_TIME_ADVANCE = 250
EYES_FOR_END = 3


class Game:
    __slots__ = (
        "seed",
        "rng",
        "overworld",
        "nether_world",
        "end_world",
        "player",
        "spawn_pos",
        "dimension",
        "mc_game_mode",
        "mineshaft_run",
        "mineshaft_runs",
        "saved_entrance_facing",
        "overworld_nether_portal_pos",
        "nether_spawn_pos",
        "end_dragon_pos",
        "end_entry_spawn",
        "moves_since_hunger",
        "world_time_ticks",
        "end_run",
        "victory",
        "_log",
    )

    @classmethod
    def from_snapshot(
        cls,
        seed: int,
        overworld: Overworld,
        player: Player,
        spawn_pos: Pos,
        dimension: Dimension,
        mc_game_mode: MCGameMode,
        mineshaft_runs: dict[str, MineshaftRun],
        mineshaft_run: MineshaftRun | None,
        saved_entrance_facing: Direction,
        overworld_nether_portal_pos: Pos,
        nether_spawn_pos: Pos | None,
        nether_world: Overworld | None,
        end_world: Overworld | None,
        end_dragon_pos: Pos | None,
        end_entry_spawn: Pos | None,
        moves_since_hunger: int,
        world_time_ticks: int,
        log: list[str],
        *,
        end_run: EndRun | None = None,
        victory: bool = False,
    ) -> Game:
        g = cls.__new__(cls)
        g.seed = seed
        g.rng = random.Random(seed)
        g.overworld = overworld
        g.nether_world = nether_world
        g.end_world = end_world
        g.player = player
        g.spawn_pos = spawn_pos
        g.dimension = dimension
        g.mc_game_mode = mc_game_mode
        g.mineshaft_runs = mineshaft_runs
        g.mineshaft_run = mineshaft_run
        g.saved_entrance_facing = saved_entrance_facing
        g.overworld_nether_portal_pos = overworld_nether_portal_pos
        g.nether_spawn_pos = nether_spawn_pos
        g.end_dragon_pos = end_dragon_pos
        g.end_entry_spawn = end_entry_spawn
        g.moves_since_hunger = moves_since_hunger
        g.world_time_ticks = world_time_ticks
        g.end_run = end_run
        g.victory = victory
        g._log = list(log)
        return g

    def __init__(self, seed: int | None = None) -> None:
        self.seed = seed if seed is not None else random.randrange(1, 2**31 - 1)
        self.rng = random.Random(self.seed)
        ow, (px, py) = generate_overworld(self.rng, self.seed)
        self.overworld = ow
        self.spawn_pos = Pos(px, py)
        self.player = Player(pos=Pos(px, py), facing=Direction.N)
        self.dimension: Dimension = "overworld"
        self.mc_game_mode: MCGameMode = "survival"
        self.mineshaft_run: MineshaftRun | None = None
        self.mineshaft_runs: dict[str, MineshaftRun] = {}
        self.saved_entrance_facing = Direction.N
        self.overworld_nether_portal_pos = self._scan_nether_portal_tile()
        self.nether_spawn_pos: Pos | None = None
        self.nether_world: Overworld | None = None
        self.end_world: Overworld | None = None
        self.end_dragon_pos: Pos | None = None
        self.end_entry_spawn: Pos | None = None
        self.moves_since_hunger = 0
        self.world_time_ticks = 0
        self.end_run: EndRun | None = None
        self.victory = False
        self._log: list[str] = []
        self.log(
            "WASD step · Space mine/strike · E interact · C craft · F eat · G game mode"
        )
        self.log("Eye of Ender: craft blaze powder + ender pearl (dungeon + Nether loot).")

    def _scan_nether_portal_tile(self) -> Pos:
        for y in range(self.overworld.height):
            for x in range(self.overworld.width):
                if self.overworld.tile_at(Pos(x, y)).kind is TileKind.NETHER_PORTAL:
                    return Pos(x, y)
        return Pos(self.spawn_pos.x, self.spawn_pos.y)

    def _living_world(self) -> Overworld:
        if self.dimension == "overworld":
            return self.overworld
        if self.dimension == "nether":
            assert self.nether_world is not None
            return self.nether_world
        if self.dimension == "end":
            assert self.end_world is not None
            return self.end_world
        raise AssertionError("dungeon has no top-down world")

    def _damage_enabled(self) -> bool:
        return self.mc_game_mode in ("survival", "adventure")

    def _hunger_enabled(self) -> bool:
        return self.mc_game_mode in ("survival", "adventure")

    def cycle_mc_game_mode(self) -> None:
        order: tuple[MCGameMode, ...] = (
            "survival",
            "creative",
            "adventure",
            "spectator",
        )
        i = order.index(self.mc_game_mode)
        self.mc_game_mode = order[(i + 1) % len(order)]
        self.log(f"Game mode: {self.mc_game_mode}")

    @property
    def log_lines(self) -> list[str]:
        return list(self._log[-MAX_LOG:])

    def log(self, msg: str) -> None:
        self._log.append(msg)

    def respawn(self) -> None:
        settings = load_settings()
        if not settings.keep_inventory_on_respawn:
            self.player.inventory.clear()
        self.dimension = "overworld"
        self.mineshaft_run = None
        self.end_run = None
        self.victory = False
        self.end_world = None
        self.end_dragon_pos = None
        self.end_entry_spawn = None
        self.player.pos = Pos(self.spawn_pos.x, self.spawn_pos.y)
        self.player.facing = Direction.N
        self.player.hp = self.player.max_hp
        self.player.hunger = self.player.max_hunger
        if settings.keep_inventory_on_respawn:
            self.log("You respawn at world spawn.")
        else:
            self.log("You respawn at world spawn. Your inventory is gone.")

    def _note_dungeon_visit(self) -> None:
        run = self.mineshaft_run
        if run is None:
            return
        rid = run.current_room
        if rid not in run.visited_room_ids:
            run.visited_room_ids.append(rid)

    def _hunger_tick(self) -> None:
        self.world_time_ticks += WORLD_TIME_ADVANCE
        if not self._hunger_enabled():
            return
        self.moves_since_hunger += 1
        if self.moves_since_hunger >= 12:
            self.moves_since_hunger = 0
            if self.player.hunger > 0:
                self.player.hunger -= 1
            else:
                if self._damage_enabled():
                    self.player.hp = max(0, self.player.hp - 1)
                    self.log("You are starving.")
                    if self.player.hp <= 0:
                        self.log("You succumb to hunger.")
                        self.respawn()

    def move_topdown(self, d: MoveDir) -> None:
        if self.dimension not in ("overworld", "nether", "end"):
            return
        world = self._living_world()
        dir_map = {"N": Direction.N, "S": Direction.S, "W": Direction.W, "E": Direction.E}
        direction = dir_map[d]
        prev = self.player.facing
        self.player.facing = direction
        if direction != prev:
            return
        npos = self.player.pos.offset(direction.dx, direction.dy)
        if not world.in_bounds(npos):
            self.log("Blocked.")
            return
        key = (npos.x, npos.y)
        if key in world.mobs:
            if not self._damage_enabled():
                self.log("Mob ignored (creative/spectator).")
                return
            mob = world.mobs[key]
            new_hp, mob_left, defeated = resolve_overworld_melee(
                self.player.inventory,
                mob.hp,
                mob.atk,
                self.player.hp,
                self.rng,
            )
            self.player.hp = new_hp
            if not defeated:
                self.log("You exchange blows and fall back.")
                if self.player.hp <= 0:
                    self.log("You fall in battle.")
                    self.respawn()
                return
            del world.mobs[key]
            self.log(f"Defeated {mob.kind}.")
            if self.dimension == "nether" and self.rng.random() < 0.45:
                self.player.inventory.add(ItemId.BLAZE_POWDER, 1)
                self.log("Dropped blaze powder.")
            if self.player.hp <= 0:
                self.log("You fall in battle.")
                self.respawn()
                return
            t = world.tile_at(npos)
            if t.blocks_movement():
                return
            self.player.pos = npos
            if self.dimension == "overworld":
                self._maybe_random_encounter_at_new_cell()
            self._hunger_tick()
            return

        t = world.tile_at(npos)
        if t.blocks_movement():
            self.log("Blocked.")
            return
        self.player.pos = npos
        if self.dimension == "overworld":
            self._maybe_random_encounter_at_new_cell()
        self._hunger_tick()

    def _maybe_random_encounter_at_new_cell(self) -> None:
        p = self.player.pos
        if self.overworld.biome_at(p) is not BiomeKind.FOREST:
            return
        enc = mob_catalog_mod.MOBS.overworld_encounter
        if self.rng.random() > enc.chance:
            return
        candidates: list[Pos] = []
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            np = p.offset(dx, dy)
            if not self.overworld.in_bounds(np):
                continue
            k = (np.x, np.y)
            if k in self.overworld.mobs or self.overworld.cave_to_mineshaft_id.get(k):
                continue
            if self.overworld.tile_at(np).blocks_movement():
                continue
            candidates.append(np)
        if not candidates:
            return
        spot = self.rng.choice(candidates)
        key = (spot.x, spot.y)
        kind = self.rng.choice(enc.kinds)
        hp = self.rng.randint(enc.hp_min, enc.hp_max)
        atk = self.rng.randint(enc.atk_min, enc.atk_max)
        self.overworld.mobs[key] = OverworldMob(kind=kind, hp=hp, max_hp=hp, atk=atk)
        self.log(f"A {kind} appears nearby!")

    def mine_forward(self) -> None:
        if self.dimension == "end" and self.end_run is not None and not self.victory:
            self.end_strike_dragon()
            return
        if self.dimension not in ("overworld", "nether", "end"):
            return
        world = self._living_world()
        d = self.player.facing
        tpos = self.player.pos.offset(d.dx, d.dy)
        if not world.in_bounds(tpos):
            self.log("Nothing to mine.")
            return
        tile = world.tile_at(tpos)
        if not tile.mineable() or not can_mine_tile(self.player.inventory, tile.kind):
            self.log("You cannot mine that.")
            return
        new_tile, drops = mine_tile(self.player.inventory, self.rng, tile)
        for item, n in drops:
            if n > 0:
                self.player.inventory.add(item, n)
                self.log(f"+{n} {item}")
        world.set_tile(tpos, new_tile)
        self._hunger_tick()

    def end_strike_dragon(self) -> None:
        if self.dimension != "end" or self.end_run is None:
            return
        if self.victory:
            self.log("The dragon is already defeated.")
            return
        if not self._damage_enabled():
            self.log("No combat in this game mode.")
            return
        er = self.end_run
        d_hp, p_hp, new_ph, defeated = resolve_end_dragon_exchange(
            self.player.inventory,
            er.dragon_hp,
            self.player.hp,
            self.rng,
            er.phase,
        )
        er.dragon_hp = d_hp
        er.phase = new_ph
        self.player.hp = p_hp
        if defeated:
            self.victory = True
            self.log("The Ender Dragon falls. You have won!")
        else:
            self.log(
                f"You strike the dragon (it has {er.dragon_hp} HP left). The dragon hits back!"
            )
            if self.player.hp <= 0:
                self.log("You fall.")
                self.respawn()
        self._hunger_tick()

    def _enter_nether_topdown(self) -> None:
        if self.nether_world is None:
            self.nether_world, nspawn = generate_nether_world(self.rng, self.seed)
            self.nether_spawn_pos = nspawn
        assert self.nether_spawn_pos is not None
        self.dimension = "nether"
        self.player.pos = Pos(self.nether_spawn_pos.x, self.nether_spawn_pos.y)
        self.player.facing = Direction.N
        self.log("You step through the portal into the Nether.")

    def _enter_end_from_nether(self) -> None:
        inv = self.player.inventory
        if inv.count(ItemId.EYE_OF_ENDER) < EYES_FOR_END:
            self.log("You need 3 Eyes of Ender to open the End portal.")
            return
        inv.remove(ItemId.EYE_OF_ENDER, EYES_FOR_END)
        assert self.nether_world is not None
        if self.end_world is None:
            self.end_world, espawn, dpos = generate_end_world(self.rng, self.seed)
            self.end_dragon_pos = dpos
            self.end_entry_spawn = espawn
        assert self.end_dragon_pos is not None
        assert self.end_entry_spawn is not None
        self.end_run = EndRun(
            dragon_hp=DRAGON_MAX_HP,
            dragon_max_hp=DRAGON_MAX_HP,
            phase=0,
        )
        self.dimension = "end"
        self.player.pos = Pos(self.end_entry_spawn.x, self.end_entry_spawn.y)
        self.player.facing = Direction.N
        self.log("You enter the End. The Ender Dragon circles above the island!")

    def interact(self) -> None:
        if self.dimension == "overworld":
            t = self.overworld.tile_at(self.player.pos)
            if t.kind is TileKind.CAVE_ENTRANCE:
                mid = self.overworld.cave_to_mineshaft_id[(self.player.pos.x, self.player.pos.y)]
                if mid not in self.mineshaft_runs:
                    tier = self.rng.randint(0, 2)
                    self.mineshaft_runs[mid] = generate_mineshaft(
                        self.rng,
                        mid,
                        tier,
                        (self.player.pos.x, self.player.pos.y),
                    )
                self.mineshaft_run = self.mineshaft_runs[mid]
                self.dimension = "dungeon"
                self.saved_entrance_facing = self.player.facing
                self.log("You descend into the abandoned mineshaft.")
                self._maybe_resolve_dungeon_room()
                self._note_dungeon_visit()
            elif t.kind is TileKind.NETHER_PORTAL:
                self._enter_nether_topdown()
            else:
                self.log("Nothing to interact with.")
        elif self.dimension == "dungeon":
            assert self.mineshaft_run is not None
            room = self.mineshaft_run.rooms[self.mineshaft_run.current_room]
            if room.exit_to_overworld:
                self.dimension = "overworld"
                x, y = self.mineshaft_run.overworld_return
                self.player.pos = Pos(x, y)
                self.player.facing = self.saved_entrance_facing
                self.mineshaft_run = None
                self.log("You climb back to the surface.")
            else:
                self.log("No ladder here — find the escape shaft.")
        elif self.dimension == "nether":
            assert self.nether_world is not None
            t = self.nether_world.tile_at(self.player.pos)
            if t.kind is TileKind.NETHER_PORTAL:
                self.dimension = "overworld"
                self.player.pos = Pos(
                    self.overworld_nether_portal_pos.x,
                    self.overworld_nether_portal_pos.y,
                )
                self.player.facing = Direction.N
                self.log("You return through the portal to the Overworld.")
            elif t.kind is TileKind.END_GATE:
                self._enter_end_from_nether()
            else:
                self.log("Nothing to interact with here.")
        else:
            assert self.dimension == "end"
            if self.victory:
                self.dimension = "overworld"
                self.end_run = None
                self.end_world = None
                self.end_dragon_pos = None
                self.end_entry_spawn = None
                self.player.pos = Pos(self.spawn_pos.x, self.spawn_pos.y)
                self.player.facing = Direction.N
                self.log("You step through the light and return home.")
            else:
                self.log("Press Space to strike the dragon.")

    def dungeon_go(self, exit_label: str) -> None:
        if self.dimension != "dungeon" or self.mineshaft_run is None:
            return
        dg = self.mineshaft_run
        room = dg.rooms[dg.current_room]
        if exit_label not in room.exits:
            self.log("No passage that way.")
            return
        nxt = room.exits[exit_label]
        dg.current_room = nxt
        self.log(f"→ {dg.rooms[nxt].title}")
        self._maybe_resolve_dungeon_room()
        self._note_dungeon_visit()
        self._hunger_tick()

    def _maybe_resolve_dungeon_room(self) -> None:
        dg = self.mineshaft_run
        assert dg is not None
        room = dg.rooms[dg.current_room]
        if room.mob_kind and room.mob_hp > 0:
            if not self._damage_enabled():
                self.log("Hostile presence (no combat in this game mode).")
                return
            self.log(f"Hostile: {room.mob_kind}!")
            while room.mob_hp > 0 and self.player.hp > 0:
                room.mob_hp -= nether_player_damage(self.player.inventory) + self.rng.randint(
                    0, 2
                )
                if room.mob_hp <= 0:
                    self.log("Enemy defeated.")
                    if self.rng.random() < 0.5:
                        self.player.inventory.add(ItemId.BLAZE_POWDER, 1)
                        self.log("Dropped blaze powder.")
                    if room.loot_id and not room.loot_taken:
                        self.player.inventory.add(room.loot_id, 1)
                        self.log(f"Found {room.loot_id}.")
                        room.loot_taken = True
                    break
                self.player.hp -= room.mob_atk + self.rng.randint(0, 1)
                self.log(f"You are hit (HP {self.player.hp}).")
            if self.player.hp <= 0:
                self.log("You collapse in the dark.")
                self.respawn()

    def craft_by_index(self, idx: int) -> bool:
        if idx < 0 or idx >= len(items_mod.RECIPES):
            return False
        r = items_mod.RECIPES[idx]
        if try_craft(self.player.inventory, r):
            self.log(f"Crafted {r.produces} x{r.count}.")
            return True
        self.log("Cannot craft that.")
        return False

    def eat_if_any(self) -> bool:
        inv = self.player.inventory
        for food in (ItemId.COOKED_MEAT, ItemId.BREAD, ItemId.APPLE, ItemId.RAW_MEAT):
            if inv.count(food) > 0:
                inv.remove(food, 1)
                if food is ItemId.COOKED_MEAT:
                    gain = 6
                elif food is ItemId.BREAD:
                    gain = 5
                elif food is ItemId.APPLE:
                    gain = 4
                else:
                    gain = 2
                self.player.hunger = min(self.player.max_hunger, self.player.hunger + gain)
                self.player.hp = min(self.player.max_hp, self.player.hp + 1)
                self.log(f"Ate {food}.")
                return True
        self.log("No food.")
        return False
