from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, RichLog, Static

from mineshaft.domain.direction import Direction
from mineshaft.persistence.save import load_game, save_game
from mineshaft.sim.engine import MAX_LOG, Game, MoveDir
from mineshaft.ui.constants import DEFAULT_SAVE
from mineshaft.ui.crafting_screen import CraftingScreen
from mineshaft.ui.render import render_hud, render_mineshaft, render_overworld, render_sidebar

_MOVE_TO_DIR: dict[str, Direction] = {
    "N": Direction.N,
    "S": Direction.S,
    "W": Direction.W,
    "E": Direction.E,
}
_MOVE_TO_EXIT = {"N": "north", "S": "south", "W": "west", "E": "east"}


class GameplayScreen(Screen[None]):
    CSS = """
    #main { width: 100%; height: 1fr; }
    #main > Horizontal { height: 1fr; width: 100%; }
    #map { width: 1fr; height: 100%; min-width: 42; }
    #side { width: 40; height: 100%; }
    #hud { width: 100%; height: 1; }
    RichLog { height: 10; border: solid gray; }
    """

    BINDINGS = [
        Binding("w", "mv_n", "N", show=False),
        Binding("s", "mv_s", "S", show=False),
        Binding("a", "mv_w", "W", show=False),
        Binding("d", "mv_e", "E", show=False),
        Binding("up", "mv_n", priority=True),
        Binding("down", "mv_s", priority=True),
        Binding("left", "mv_w", priority=True),
        Binding("right", "mv_e", priority=True),
        Binding("space", "mine", "Mine"),
        Binding("e", "interact", "Act"),
        Binding("c", "craft_menu", "Craft"),
        Binding("f", "eat", "Eat"),
        Binding("S", "save", "Save"),
        Binding("L", "load", "Load"),
        Binding("f3", "toggle_debug", "Debug", show=False),
        Binding("g", "cycle_gamemode", "GameMode", show=False),
    ]

    def __init__(self, game: Game) -> None:
        super().__init__()
        self.game = game
        self._debug_overlay = False
        self._last_synced_log_len = 0

    def compose(self) -> ComposeResult:
        yield Header(name="mineshaft")
        with Vertical(id="main"):
            with Horizontal():
                yield Static("", id="map")
                with Vertical(id="side"):
                    yield Static("", id="sidebar")
                    yield RichLog(id="log", highlight=True, markup=True)
            yield Static("", id="hud")
        yield Footer()

    def on_mount(self) -> None:
        self._log_w = self.query_one(RichLog)
        for line in self.game.log_lines:
            self._log_w.write(line)
        self.refresh_all()

    def action_help(self) -> None:
        self.game.log(
            "WASD step · Space mine · E interact · C craft · F eat · G cycle game mode"
        )
        self.game.log("Shift+S save · Shift+L load")
        self._sync_log()

    def _sync_log(self) -> None:
        """Update RichLog incrementally when possible; full refresh when the window slides."""
        log = self.query_one(RichLog)
        g = self.game
        n = len(g._log)
        if n == self._last_synced_log_len:
            return
        if n < self._last_synced_log_len:
            log.clear()
            for line in g.log_lines:
                log.write(line)
            self._last_synced_log_len = n
            return
        if n <= MAX_LOG:
            for i in range(self._last_synced_log_len, n):
                log.write(g._log[i])
        else:
            log.clear()
            for line in g.log_lines:
                log.write(line)
        self._last_synced_log_len = n

    def _viewport_radii(self) -> tuple[int, int]:
        try:
            static = self.query_one("#map", Static)
            sw, sh = static.size.width, static.size.height
        except Exception:
            sw, sh = 21, 21
        if sw < 3 or sh < 3:
            sw, sh = 21, 21
        rw = max(1, min(100, (sw - 1) // 2))
        rh = max(1, min(50, (sh - 1) // 2))
        return rw, rh

    def refresh_all(self) -> None:
        g = self.game
        mp = self.query_one("#map", Static)
        side = self.query_one("#sidebar", Static)
        hud = self.query_one("#hud", Static)
        rw, rh = self._viewport_radii()
        if g.dimension == "dungeon":
            assert g.mineshaft_run is not None
            mp.update(render_mineshaft(g.mineshaft_run))
        elif g.dimension == "overworld":
            mp.update(render_overworld(g.overworld, g.player, rw, rh))
        elif g.dimension == "nether":
            assert g.nether_world is not None
            mp.update(render_overworld(g.nether_world, g.player, rw, rh))
        else:
            assert g.dimension == "end"
            assert g.end_world is not None
            dr = g.end_dragon_pos if (g.end_run is not None and not g.victory) else None
            mp.update(
                render_overworld(g.end_world, g.player, rw, rh, dragon_at=dr)
            )
        side.update(render_sidebar(g, show_debug=self._debug_overlay))
        hw = max(42, hud.size.width)
        hud.update(render_hud(g.player, hw))
        self._sync_log()

    def on_resize(self, event: events.Resize) -> None:
        self.refresh_all()

    def action_toggle_debug(self) -> None:
        self._debug_overlay = not self._debug_overlay
        self.refresh_all()

    def _move(self, d: MoveDir) -> None:
        if self.game.player.hp <= 0:
            return
        if self.game.dimension == "dungeon":
            direction = _MOVE_TO_DIR[d]
            prev = self.game.player.facing
            self.game.player.facing = direction
            if direction != prev:
                self.refresh_all()
                return
            self.game.dungeon_go(_MOVE_TO_EXIT[d])
        elif self.game.dimension in ("overworld", "nether", "end"):
            self.game.move_topdown(d)
        self.refresh_all()

    def action_mv_n(self) -> None:
        self._move("N")

    def action_mv_s(self) -> None:
        self._move("S")

    def action_mv_w(self) -> None:
        self._move("W")

    def action_mv_e(self) -> None:
        self._move("E")

    def action_mine(self) -> None:
        if self.game.player.hp <= 0:
            return
        self.game.mine_forward()
        self.refresh_all()

    def action_interact(self) -> None:
        if self.game.player.hp <= 0:
            return
        self.game.interact()
        self.refresh_all()

    def action_eat(self) -> None:
        if self.game.player.hp <= 0:
            return
        self.game.eat_if_any()
        self.refresh_all()

    def action_craft_menu(self) -> None:
        self.app.push_screen(CraftingScreen(self.game), self._after_craft_screen)

    def _after_craft_screen(self, _result: None) -> None:
        self.refresh_all()

    def action_cycle_gamemode(self) -> None:
        self.game.cycle_mc_game_mode()
        self._sync_log()
        self.refresh_all()

    def action_save(self) -> None:
        save_game(DEFAULT_SAVE, self.game)
        self.game.log(f"Saved to {DEFAULT_SAVE.resolve()}")
        self._sync_log()

    def action_load(self) -> None:
        if not DEFAULT_SAVE.is_file():
            self.game.log("No save file found.")
            self._sync_log()
            return
        self.game = load_game(DEFAULT_SAVE)
        self._last_synced_log_len = 0
        self.query_one(RichLog).clear()
        self.game.log("Loaded save.")
        self.refresh_all()
