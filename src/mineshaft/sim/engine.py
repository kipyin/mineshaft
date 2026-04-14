from __future__ import annotations

import random
from typing import Literal

from mineshaft.config import load_settings
from mineshaft.domain.direction import Direction
from mineshaft.domain.items import ItemId
from mineshaft.domain.mineshaft_run import MineshaftRun
from mineshaft.domain.overworld import Overworld, OverworldMob
from mineshaft.domain.player import Player
from mineshaft.domain.pos import Pos
from mineshaft.domain.tiles import BiomeKind, TileKind
from mineshaft.gen.mineshaft_gen import generate_mineshaft
from mineshaft.gen.overworld_gen import generate_overworld
from mineshaft.sim.combat import mineshaft_player_damage, resolve_overworld_melee
from mineshaft.sim.crafting import try_craft
from mineshaft.sim.mining import can_mine_tile, mine_tile

MoveDir = Literal["N", "S", "E", "W"]
MAX_LOG = 80
# Minecraft-style day length; advances with hunger ticks (player actions).
WORLD_TIME_ADVANCE = 250


class Game:
    __slots__ = (
        "seed",
        "rng",
        "overworld",
        "player",
        "spawn_pos",
        "mode",
        "mineshaft_run",
        "mineshaft_runs",
        "saved_entrance_facing",
        "moves_since_hunger",
        "world_time_ticks",
        "_log",
    )

    @classmethod
    def from_snapshot(
        cls,
        seed: int,
        overworld: Overworld,
        player: Player,
        spawn_pos: Pos,
        mode: Literal["overworld", "mineshaft"],
        mineshaft_runs: dict[str, MineshaftRun],
        mineshaft_run: MineshaftRun | None,
        saved_entrance_facing: Direction,
        moves_since_hunger: int,
        world_time_ticks: int,
        log: list[str],
    ) -> Game:
        g = cls.__new__(cls)
        g.seed = seed
        g.rng = random.Random(seed)
        g.overworld = overworld
        g.player = player
        g.spawn_pos = spawn_pos
        g.mode = mode
        g.mineshaft_runs = mineshaft_runs
        g.mineshaft_run = mineshaft_run
        g.saved_entrance_facing = saved_entrance_facing
        g.moves_since_hunger = moves_since_hunger
        g.world_time_ticks = world_time_ticks
        g._log = list(log)
        return g

    def __init__(self, seed: int | None = None) -> None:
        self.seed = seed if seed is not None else random.randrange(1, 2**31 - 1)
        self.rng = random.Random(self.seed)
        ow, (px, py) = generate_overworld(self.rng, self.seed)
        self.overworld = ow
        self.spawn_pos = Pos(px, py)
        self.player = Player(pos=Pos(px, py), facing=Direction.N)
        self.mode: Literal["overworld", "mineshaft"] = "overworld"
        self.mineshaft_run: MineshaftRun | None = None
        self.mineshaft_runs: dict[str, MineshaftRun] = {}
        self.saved_entrance_facing = Direction.N
        self.moves_since_hunger = 0
        self.world_time_ticks = 0
        self._log: list[str] = []
        self.log("WASD move · Space mine ahead · E interact/take exit · C craft · F eat")

    @property
    def log_lines(self) -> list[str]:
        return list(self._log[-MAX_LOG:])

    def log(self, msg: str) -> None:
        self._log.append(msg)

    def respawn(self) -> None:
        settings = load_settings()
        if not settings.keep_inventory_on_respawn:
            self.player.inventory.clear()
        self.mode = "overworld"
        self.mineshaft_run = None
        self.player.pos = Pos(self.spawn_pos.x, self.spawn_pos.y)
        self.player.facing = Direction.N
        self.player.hp = self.player.max_hp
        self.player.hunger = self.player.max_hunger
        if settings.keep_inventory_on_respawn:
            self.log("You respawn at world spawn.")
        else:
            self.log("You respawn at world spawn. Your inventory is gone.")

    def _note_mineshaft_visit(self) -> None:
        run = self.mineshaft_run
        if run is None:
            return
        rid = run.current_room
        if rid not in run.visited_room_ids:
            run.visited_room_ids.append(rid)

    def _hunger_tick(self) -> None:
        self.world_time_ticks += WORLD_TIME_ADVANCE
        self.moves_since_hunger += 1
        if self.moves_since_hunger >= 12:
            self.moves_since_hunger = 0
            if self.player.hunger > 0:
                self.player.hunger -= 1
            else:
                self.player.hp = max(0, self.player.hp - 1)
                self.log("You are starving.")
                if self.player.hp <= 0:
                    self.log("You succumb to hunger.")
                    self.respawn()

    def move_overworld(self, d: MoveDir) -> None:
        dir_map = {"N": Direction.N, "S": Direction.S, "W": Direction.W, "E": Direction.E}
        direction = dir_map[d]
        self.player.facing = direction
        npos = self.player.pos.offset(direction.dx, direction.dy)
        if not self.overworld.in_bounds(npos):
            self.log("Blocked.")
            return
        key = (npos.x, npos.y)
        if key in self.overworld.mobs:
            mob = self.overworld.mobs[key]
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
            del self.overworld.mobs[key]
            self.log(f"Defeated {mob.kind}.")
            if self.rng.random() < 0.45:
                self.player.inventory.add(ItemId.RAW_MEAT, 1)
                self.log("Dropped raw meat.")
            if self.player.hp <= 0:
                self.log("You fall in battle.")
                self.respawn()
                return
            t = self.overworld.tile_at(npos)
            if t.blocks_movement():
                return
            self.player.pos = npos
            self._maybe_random_encounter_at_new_cell()
            self._hunger_tick()
            return

        t = self.overworld.tile_at(npos)
        if t.blocks_movement():
            self.log("Blocked.")
            return
        self.player.pos = npos
        self._maybe_random_encounter_at_new_cell()
        self._hunger_tick()

    def _maybe_random_encounter_at_new_cell(self) -> None:
        p = self.player.pos
        if self.overworld.biome_at(p) is not BiomeKind.FOREST:
            return
        if self.rng.random() > 0.055:
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
        kind = self.rng.choice(["crawler", "stray"])
        hp = self.rng.randint(3, 7)
        atk = self.rng.randint(1, 3)
        self.overworld.mobs[key] = OverworldMob(kind=kind, hp=hp, max_hp=hp, atk=atk)
        self.log(f"A {kind} appears nearby!")

    def mine_forward(self) -> None:
        if self.mode != "overworld":
            return
        d = self.player.facing
        tpos = self.player.pos.offset(d.dx, d.dy)
        if not self.overworld.in_bounds(tpos):
            self.log("Nothing to mine.")
            return
        tile = self.overworld.tile_at(tpos)
        if not tile.mineable() or not can_mine_tile(self.player.inventory, tile.kind):
            self.log("You cannot mine that.")
            return
        new_tile, drops = mine_tile(self.player.inventory, self.rng, tile)
        for item, n in drops:
            if n > 0:
                self.player.inventory.add(item, n)
                self.log(f"+{n} {item}")
        self.overworld.set_tile(tpos, new_tile)
        self._hunger_tick()

    def interact(self) -> None:
        if self.mode == "overworld":
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
                self.mode = "mineshaft"
                self.saved_entrance_facing = self.player.facing
                self.log("You descend into the abandoned mineshaft.")
                self._maybe_resolve_mineshaft_room()
                self._note_mineshaft_visit()
            else:
                self.log("Nothing to interact with.")
        else:
            assert self.mineshaft_run is not None
            room = self.mineshaft_run.rooms[self.mineshaft_run.current_room]
            if room.exit_to_overworld:
                self.mode = "overworld"
                x, y = self.mineshaft_run.overworld_return
                self.player.pos = Pos(x, y)
                self.player.facing = self.saved_entrance_facing
                self.mineshaft_run = None
                self.log("You climb back to the surface.")
            else:
                self.log("No ladder here — find the escape shaft.")

    def mineshaft_go(self, exit_label: str) -> None:
        if self.mode != "mineshaft" or self.mineshaft_run is None:
            return
        dg = self.mineshaft_run
        room = dg.rooms[dg.current_room]
        if exit_label not in room.exits:
            self.log("No passage that way.")
            return
        nxt = room.exits[exit_label]
        dg.current_room = nxt
        self.log(f"→ {dg.rooms[nxt].title}")
        self._maybe_resolve_mineshaft_room()
        self._note_mineshaft_visit()
        self._hunger_tick()

    def _maybe_resolve_mineshaft_room(self) -> None:
        dg = self.mineshaft_run
        assert dg is not None
        room = dg.rooms[dg.current_room]
        if room.mob_kind and room.mob_hp > 0:
            self.log(f"Hostile: {room.mob_kind}!")
            while room.mob_hp > 0 and self.player.hp > 0:
                room.mob_hp -= mineshaft_player_damage(self.player.inventory) + self.rng.randint(
                    0, 2
                )
                if room.mob_hp <= 0:
                    self.log("Enemy defeated.")
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
        from mineshaft.domain.items import RECIPES

        if idx < 0 or idx >= len(RECIPES):
            return False
        r = RECIPES[idx]
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
