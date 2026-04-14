from __future__ import annotations

from pathlib import Path

import typer

from mineshaft.persistence.save import load_game
from mineshaft.ui.app import run_app

cli = typer.Typer(help="Terminal mineshaft — explore, mine, survive.")


@cli.callback(invoke_without_command=True)
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        run_app()


@cli.command()
def play(
    seed: int | None = typer.Option(None, "--seed", "-s", help="Random seed for world gen"),
) -> None:
    """Start a new game."""
    run_app(seed=seed)


@cli.command("load")
def load_cmd(
    path: Path = typer.Argument(Path("mineshaft_save.json"), help="Save file to load"),
) -> None:
    """Load a saved game and play."""
    if not path.is_file():
        raise typer.BadParameter(f"Save file not found: {path}")
    run_app(game=load_game(path))


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
