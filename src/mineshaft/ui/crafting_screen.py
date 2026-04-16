from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from mineshaft.domain.items import item_name
from mineshaft.sim.crafting import list_craftable
from mineshaft.sim.engine import Game


class CraftingScreen(ModalScreen[None]):
    """Modal: inventory list and craftable recipes; 1–9 crafts while focused."""

    CSS = """
    CraftingScreen {
        align: center middle;
    }
    #craft-panel {
        width: 88;
        max-width: 90%;
        max-height: 90%;
        border: heavy $accent;
        background: $surface;
        padding: 1 2;
    }
    #craft-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    #craft-columns {
        height: auto;
        min-height: 12;
    }
    #craft-inv {
        width: 1fr;
        height: auto;
        border: solid $primary;
        padding: 0 1;
    }
    #craft-recipes {
        width: 2fr;
        height: auto;
        border: solid $primary;
        padding: 0 1;
    }
    #craft-hint {
        text-align: center;
        margin-top: 1;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("c", "close", "Close", show=False),
    ]

    def __init__(self, game: Game) -> None:
        super().__init__()
        self.game = game

    def compose(self) -> ComposeResult:
        with Vertical(id="craft-panel"):
            yield Static("Crafting", id="craft-title")
            with Horizontal(id="craft-columns"):
                yield Static("", id="craft-inv")
                yield Static("", id="craft-recipes")
            yield Static("1–9 craft   Esc or C close", id="craft-hint")

    def on_mount(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        inv = self.game.player.inventory.counts
        inv_lines = ["Inventory", ""]
        if not inv:
            inv_lines.append("  (empty)")
        else:
            for k in sorted(inv):
                inv_lines.append(f"  {item_name(k)}  x{inv[k]}")
        self.query_one("#craft-inv", Static).update("\n".join(inv_lines))

        craftable = list_craftable(self.game.player.inventory)
        rlines = ["Craftable", ""]
        if not craftable:
            rlines.append("  (nothing craftable)")
        else:
            for i, (_idx, rec) in enumerate(craftable[:9]):
                needs = ", ".join(f"{item_name(k)} x{v}" for k, v in sorted(rec.needs.items()))
                rlines.append(f"  [{i + 1}] {item_name(rec.produces)} x{rec.count}")
                rlines.append(f"       needs: {needs}")
        self.query_one("#craft-recipes", Static).update("\n".join(rlines))

    def action_close(self) -> None:
        self.dismiss()

    def on_key(self, event: events.Key) -> None:
        if event.key not in ("1", "2", "3", "4", "5", "6", "7", "8", "9"):
            return
        craftable = list_craftable(self.game.player.inventory)
        n = int(event.key)
        if len(craftable) >= n:
            recipe_idx = craftable[n - 1][0]
            self.game.craft_by_index(recipe_idx)
            self._refresh()
        event.stop()
