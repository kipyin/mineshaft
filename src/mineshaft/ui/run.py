from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mineshaft.sim.engine import Game


def run_app(
    seed: int | None = None,
    game: Game | None = None,
    *,
    show_menu: bool = True,
) -> None:
    """Start the Textual UI. Imports the app lazily so CLI --help stays fast."""
    from mineshaft.ui.app import MineshaftApp

    MineshaftApp(seed=seed, game=game, show_menu=show_menu).run()
