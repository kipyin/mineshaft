from __future__ import annotations

from pathlib import Path

import typer

cli = typer.Typer(help="Terminal mineshaft — explore, mine, survive.")


@cli.callback(invoke_without_command=True)
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        from mineshaft.ui.run import run_app

        run_app()


@cli.command()
def play(
    seed: int | None = typer.Option(None, "--seed", "-s", help="Random seed for world gen"),
) -> None:
    """Start a new game."""
    from mineshaft.ui.run import run_app

    run_app(seed=seed, show_menu=False)


@cli.command("load")
def load_cmd(
    path: Path = typer.Argument(Path("mineshaft_save.json"), help="Save file to load"),
) -> None:
    """Load a saved game and play."""
    if not path.is_file():
        raise typer.BadParameter(f"Save file not found: {path}")
    from mineshaft.persistence.save import load_game
    from mineshaft.ui.run import run_app

    run_app(game=load_game(path), show_menu=False)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
