from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import CenterMiddle, Container, Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Input, Label, OptionList, Static, Switch
from textual.widgets.option_list import Option

from mineshaft.config import Settings, load_settings, save_settings
from mineshaft.persistence.save import load_game
from mineshaft.sim.engine import Game
from mineshaft.ui.constants import DEFAULT_SAVE


def _app_version() -> str:
    try:
        from importlib.metadata import PackageNotFoundError, version

        return version("mineshaft")
    except PackageNotFoundError:
        return "0.1.0"


class SeedModal(ModalScreen[bool | int | None]):
    """Dismiss: False=cancel, None=random seed, int=explicit seed."""

    DEFAULT_CSS = """
    SeedModal {
        align: center middle;
    }
    #dialog {
        width: 50;
        max-width: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    #buttons {
        height: auto;
        margin-top: 1;
    }
    #buttons Button {
        margin-right: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("World seed (empty = random)")
            yield Input(placeholder="optional integer", id="seed_input")
            with Horizontal(id="buttons"):
                yield Button("Start", variant="primary", id="start")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(False)
            return
        if event.button.id != "start":
            return
        raw = self.query_one("#seed_input", Input).value.strip()
        if not raw:
            self.dismiss(None)
            return
        try:
            self.dismiss(int(raw))
        except ValueError:
            self.app.notify("Enter a valid integer or leave empty for random.", severity="error")


class LoadPathModal(ModalScreen[bool | Path]):
    """Dismiss: False=cancel, Path=save file to load."""

    DEFAULT_CSS = """
    LoadPathModal {
        align: center middle;
    }
    #dialog {
        width: 56;
        max-width: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    #buttons {
        height: auto;
        margin-top: 1;
    }
    #buttons Button {
        margin-right: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("Save file path")
            yield Input(value=str(DEFAULT_SAVE), id="path_input")
            with Horizontal(id="buttons"):
                yield Button("Load", variant="primary", id="load")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(False)
            return
        if event.button.id != "load":
            return
        raw = self.query_one("#path_input", Input).value.strip()
        path = Path(raw) if raw else DEFAULT_SAVE
        if not path.is_file():
            self.app.notify(f"File not found: {path}", severity="error")
            return
        self.dismiss(path)


class SettingsModal(ModalScreen[None]):
    DEFAULT_CSS = """
    SettingsModal {
        align: center middle;
    }
    #dialog {
        width: 52;
        max-width: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    #buttons {
        height: auto;
        margin-top: 1;
    }
    #buttons Button {
        margin-right: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("Gameplay")
            with Horizontal():
                yield Label("Keep inventory on respawn  ", id="ki_label")
                yield Switch(value=False, id="keep_inventory")
            with Horizontal(id="buttons"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Close", id="close")

    def on_mount(self) -> None:
        s = load_settings()
        self.query_one("#keep_inventory", Switch).value = s.keep_inventory_on_respawn

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close":
            self.dismiss()
            return
        if event.button.id != "save":
            return
        s = load_settings()
        ki = self.query_one("#keep_inventory", Switch).value
        save_settings(
            Settings(
                keep_inventory_on_respawn=ki,
                max_viewport_radius_w=s.max_viewport_radius_w,
                max_viewport_radius_h=s.max_viewport_radius_h,
            )
        )
        self.app.notify("Settings saved.")
        self.dismiss()


class HelpModal(ModalScreen[None]):
    TEXT = """\
WASD — turn; press again in that direction to step
Space — mine ahead
E — interact / take exit
C — crafting (1–9 in the window; Esc or C to close)
F — eat
Shift+S — save
Shift+L — load default save
F3 — debug overlay (in game)
"""

    DEFAULT_CSS = """
    HelpModal {
        align: center middle;
    }
    #dialog {
        width: 56;
        max-width: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("How to play")
            yield Static(self.TEXT, id="help_body")
            yield Button("OK", variant="primary", id="ok")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self.dismiss()


class AboutModal(ModalScreen[None]):
    DEFAULT_CSS = """
    AboutModal {
        align: center middle;
    }
    #dialog {
        width: 48;
        max-width: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("Mineshaft")
            yield Static(
                f"Version {_app_version()}\nTerminal exploration / mining.",
                id="about_body",
            )
            yield Button("OK", variant="primary", id="ok")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self.dismiss()


class MainMenuScreen(Screen[Game | None]):
    """Dismiss with Game to start play, or None to quit."""

    BINDINGS = [
        Binding("escape", "quit_menu", "Quit", show=True),
    ]

    DEFAULT_CSS = """
    MainMenuScreen {
        layout: vertical;
    }
    #menu_panel {
        width: auto;
        height: auto;
    }
    #menu_title {
        text-align: center;
        margin-bottom: 1;
        text-style: bold;
        width: 100%;
    }
    #menu {
        width: 42;
        height: auto;
        max-height: 80%;
        border: solid $primary;
    }
    """

    def compose(self) -> ComposeResult:
        with CenterMiddle():
            with Vertical(id="menu_panel"):
                yield Static("MINESHAFT", id="menu_title")
                yield OptionList(id="menu")
        yield Footer()

    def on_mount(self) -> None:
        self._rebuild_options()

    def _rebuild_options(self) -> None:
        ol = self.query_one("#menu", OptionList)
        ol.clear_options()
        can_continue = DEFAULT_SAVE.is_file()
        ol.add_options(
            [
                Option("New game", id="new"),
                Option("Continue", id="continue", disabled=not can_continue),
                Option("Load game…", id="load"),
                Option("Settings", id="settings"),
                Option("How to play", id="help"),
                Option("About", id="about"),
                Option("Quit", id="quit"),
            ]
        )

    def action_quit_menu(self) -> None:
        self.dismiss(None)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        oid = event.option.id or ""
        if oid == "new":
            self.app.push_screen(SeedModal(), callback=self._seed_done)
        elif oid == "continue":
            self.dismiss(load_game(DEFAULT_SAVE))
        elif oid == "load":
            self.app.push_screen(LoadPathModal(), callback=self._load_done)
        elif oid == "settings":
            self.app.push_screen(SettingsModal())
        elif oid == "help":
            self.app.push_screen(HelpModal())
        elif oid == "about":
            self.app.push_screen(AboutModal())
        elif oid == "quit":
            self.dismiss(None)
        else:
            pass

    def _seed_done(self, result: bool | int | None) -> None:
        if result is False:
            return
        self.dismiss(Game(seed=result))

    def _load_done(self, result: bool | Path) -> None:
        if result is False:
            return
        assert isinstance(result, Path)
        try:
            game = load_game(result)
        except (OSError, ValueError) as e:
            self.app.notify(f"Could not load save: {e}", severity="error")
            return
        self.dismiss(game)
