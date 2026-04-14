from __future__ import annotations

from pathlib import Path

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, RichLog, Static

from mineshaft.domain.items import item_name
from mineshaft.persistence.save import load_game, save_game
from mineshaft.sim.crafting import list_craftable
from mineshaft.sim.engine import Game, MoveDir
from mineshaft.ui.render import render_mineshaft, render_overworld, render_sidebar

DEFAULT_SAVE = Path("mineshaft_save.json")


class MineshaftApp(App[None]):
    CSS = """
    #main { width: 100%; height: 1fr; }
    #map { width: 1fr; height: 100%; min-width: 42; }
    #side { width: 40; height: 100%; }
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
    ]

    def __init__(self, game: Game | None = None, seed: int | None = None) -> None:
        super().__init__()
        self.game = game if game is not None else Game(seed=seed)
        self._debug_overlay = False

    def compose(self) -> ComposeResult:
        yield Header(name="mineshaft")
        with Horizontal(id="main"):
            yield Static("", id="map")
            with Vertical(id="side"):
                yield Static("", id="sidebar")
                yield RichLog(id="log", highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        self._log_w = self.query_one(RichLog)
        for line in self.game.log_lines:
            self._log_w.write(line)
        self.refresh_all()

    def action_help(self) -> None:
        self.game.log(
            "WASD move · Space mine · E interact · C craft list · digits craft · F eat"
        )
        self.game.log("Shift+S save · Shift+L load")
        self._sync_log()

    def _sync_log(self) -> None:
        log = self.query_one(RichLog)
        log.clear()
        for line in self.game.log_lines:
            log.write(line)

    def refresh_all(self) -> None:
        g = self.game
        mp = self.query_one("#map", Static)
        side = self.query_one("#sidebar", Static)
        if g.mode == "overworld":
            mp.update(render_overworld(g.overworld, g.player))
        else:
            assert g.mineshaft_run is not None
            mp.update(render_mineshaft(g.mineshaft_run))
        side.update(render_sidebar(g, show_debug=self._debug_overlay))
        self._sync_log()

    def action_toggle_debug(self) -> None:
        self._debug_overlay = not self._debug_overlay
        self.refresh_all()

    def _move(self, d: MoveDir) -> None:
        if self.game.player.hp <= 0:
            return
        if self.game.mode == "overworld":
            self.game.move_overworld(d)
        else:
            m = {"N": "north", "S": "south", "W": "west", "E": "east"}[d]
            self.game.mineshaft_go(m)
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
        g = self.game
        craftable = list_craftable(g.player.inventory)
        if not craftable:
            g.log("Nothing craftable right now.")
            self._sync_log()
            return
        g.log("Craftable — press number key 1-9:")
        for i, (idx, rec) in enumerate(craftable[:9]):
            needs = ", ".join(f"{item_name(k)} x{v}" for k, v in rec.needs.items())
            g.log(f"  [{i + 1}] {item_name(rec.produces)} x{rec.count}  <-  {needs}")
        self._sync_log()

    def on_key(self, event: events.Key) -> None:
        if event.key in ("1", "2", "3", "4", "5", "6", "7", "8", "9"):
            craftable = list_craftable(self.game.player.inventory)
            n = int(event.key)
            if len(craftable) >= n:
                recipe_idx = craftable[n - 1][0]
                self.game.craft_by_index(recipe_idx)
                self.refresh_all()
                event.stop()

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
        self.game.log("Loaded save.")
        self.refresh_all()


def run_app(seed: int | None = None, game: Game | None = None) -> None:
    app = MineshaftApp(seed=seed, game=game)
    app.run()
