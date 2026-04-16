from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import App, ComposeResult
from textual.widgets import Static

if TYPE_CHECKING:
    from mineshaft.sim.engine import Game


class MineshaftApp(App[None]):
    """Minimal shell; gameplay and menu modules load lazily on first screen push."""

    def __init__(
        self,
        game: Game | None = None,
        seed: int | None = None,
        *,
        show_menu: bool = True,
    ) -> None:
        super().__init__()
        self._game = game
        self._seed = seed
        self._show_menu = show_menu

    def compose(self) -> ComposeResult:
        yield Static("")

    def on_mount(self) -> None:
        if self._show_menu:
            from mineshaft.ui.menu import MainMenuScreen

            self.push_screen(MainMenuScreen(), callback=self._menu_result)
        else:
            from mineshaft.sim.engine import Game
            from mineshaft.ui.gameplay import GameplayScreen

            g = self._game if self._game is not None else Game(seed=self._seed)
            self.push_screen(GameplayScreen(g))

    def _menu_result(self, result: Game | None) -> None:
        if result is None:
            self.exit()
        else:
            from mineshaft.ui.gameplay import GameplayScreen

            self.push_screen(GameplayScreen(result))
