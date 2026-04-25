# mineshaft

Text-based Minecraft-inspired terminal game (Python 3.12+).

## Run

With [uv](https://github.com/astral-sh/uv):

```bash
uv sync
uv run mineshaft
```

Or install the package in editable mode and use the `mineshaft` entry point.

- `mineshaft` — main menu, then play
- `mineshaft play` — new game; optional `--seed` / `-s` for world generation
- `mineshaft load [PATH]` — load a save (default: `mineshaft_save.json`)

## Dev

```bash
uv run pytest
uv run ruff check .
```
