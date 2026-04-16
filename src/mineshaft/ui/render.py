from __future__ import annotations

from typing import Literal

from rich.cells import cell_len
from rich.style import Style
from rich.text import Text

from mineshaft.domain.items import item_name
from mineshaft.domain.mineshaft_run import MineshaftRun
from mineshaft.domain.overworld import Overworld
from mineshaft.domain.player import Player
from mineshaft.domain.pos import Pos
from mineshaft.domain.tiles import TileKind

MC_DAY_TICKS = 24000

# Foreground + background so tiles stay distinct even when terminal mutes "on *" alone
_TERRAIN = {
    TileKind.GRASS: Style.parse("bold green on dark_green"),
    TileKind.DIRT: Style.parse("yellow3 on yellow4"),
    TileKind.STONE: Style.parse("white on bright_black"),
    TileKind.SAND: Style.parse("bold yellow on yellow"),
    TileKind.WATER: Style.parse("bold cyan on blue"),
    TileKind.BEDROCK: Style.parse("white on black"),
    TileKind.NETHER_PORTAL: Style.parse("bold bright_magenta on purple"),
    TileKind.NETHERRACK: Style.parse("bold bright_red on black"),
    TileKind.SOUL_SAND: Style.parse("bold yellow3 on yellow4"),
    TileKind.NETHER_LAVA: Style.parse("bold white on red"),
    TileKind.END_GATE: Style.parse("bold white on black"),
    TileKind.END_STONE: Style.parse("bold white on bright_black"),
}
_TERRAIN_CHAR = {
    TileKind.GRASS: "█",
    TileKind.DIRT: "█",
    TileKind.STONE: "█",
    TileKind.SAND: "░",
    TileKind.WATER: "~",
    TileKind.BEDROCK: "█",
    TileKind.NETHER_PORTAL: "█",
    TileKind.NETHERRACK: "▓",
    TileKind.SOUL_SAND: "▒",
    TileKind.NETHER_LAVA: "~",
    TileKind.END_GATE: "⊕",
    TileKind.END_STONE: "█",
}

_ORE_COAL = Style.parse("white on bright_black")
_ORE_IRON = Style.parse("bright_yellow on bright_black")

_PLAYER = Style.parse("bold black on bright_yellow")
_OOB = Style.parse("on black")
_MOB = Style.parse("bold bright_red on dark_red")
_CAVE = Style.parse("bold bright_black on magenta")
_TREE = Style.parse("bold green on dark_green")
_DRAGON = Style.parse("bold magenta on bright_black")
_FORWARD_HI = Style.parse("reverse bold")

IconState = Literal["full", "half", "empty"]

_HUD_HEART_FULL = Style.parse("bold red")
_HUD_HEART_HALF = Style.parse("bright_yellow")
_HUD_HEART_EMPTY = Style.parse("dim white")
_HUD_FOOD_FULL = Style.parse("bold yellow")
_HUD_FOOD_HALF = Style.parse("yellow")
_HUD_FOOD_EMPTY = Style.parse("dim bright_black")

# Single-column glyphs (avoid wide emoji / ambiguous Unicode widths)
_HUD_HP_GLYPH = {"full": "#", "half": "+", "empty": "."}
_HUD_FOOD_GLYPH = {"full": "=", "half": "-", "empty": "."}


def icon_states(current: int, maximum: int) -> list[IconState]:
    """Ten slots over [0, maximum]; each slot can be full, half, or empty (MC-style)."""
    max_m = max(1, maximum)
    cur = max(0, min(current, max_m))
    out: list[IconState] = []
    for i in range(10):
        lo = i * max_m / 10
        hi = (i + 1) * max_m / 10
        if cur >= hi:
            out.append("full")
        elif cur > lo:
            out.append("half")
        else:
            out.append("empty")
    return out


def _hud_bar_text(states: list[IconState], *, health: bool) -> Text:
    t = Text()
    for s in states:
        if health:
            ch = _HUD_HP_GLYPH[s]
            if s == "full":
                t.append(ch, style=_HUD_HEART_FULL)
            elif s == "half":
                t.append(ch, style=_HUD_HEART_HALF)
            else:
                t.append(ch, style=_HUD_HEART_EMPTY)
        else:
            ch = _HUD_FOOD_GLYPH[s]
            if s == "full":
                t.append(ch, style=_HUD_FOOD_FULL)
            elif s == "half":
                t.append(ch, style=_HUD_FOOD_HALF)
            else:
                t.append(ch, style=_HUD_FOOD_EMPTY)
    return t


def render_hud(player: Player, width: int) -> Text:
    """One row: health icons left, hunger icons right (Minecraft-style)."""
    left = _hud_bar_text(icon_states(player.hp, player.max_hp), health=True)
    right = _hud_bar_text(icon_states(player.hunger, player.max_hunger), health=False)
    inner = max(0, width - cell_len(left.plain) - cell_len(right.plain))
    out = Text()
    out.append_text(left)
    out.append(" " * inner)
    out.append_text(right)
    return out


def _forward_cell(player: Player) -> Pos:
    return player.pos.offset(player.facing.dx, player.facing.dy)


def _world_time_lines(total_ticks: int) -> tuple[str, str]:
    tod = total_ticks % MC_DAY_TICKS
    day = total_ticks // MC_DAY_TICKS + 1
    if tod < 6000:
        phase = "day"
    elif tod < 12000:
        phase = "sunset"
    elif tod < 18000:
        phase = "night"
    else:
        phase = "sunrise"
    return f"Day {day}", f"Time {tod}/{MC_DAY_TICKS} ({phase})"


def format_debug_overlay(game) -> str:
    """F3-style lines: coords, look target, biome/terrain, world time."""
    p = game.player
    day_s, time_s = _world_time_lines(game.world_time_ticks)
    lines = [
        "[F3]",
        f"XYZ {p.pos.x} / {p.pos.y}",
        f"Facing {p.facing.name}",
        f"Dimension {game.dimension}  GameMode {game.mc_game_mode}",
        day_s,
        time_s,
    ]
    dim = game.dimension
    if dim == "overworld":
        ow = game.overworld
        foot = ow.tile_at(p.pos).kind.value
        bio = ow.biome_at(p.pos).name.lower()
        lines.append(f"Biome {bio}")
        lines.append(f"Terrain (feet) {foot}")
        fp = _forward_cell(p)
        if not ow.in_bounds(fp):
            lines.append("Looking at (out of bounds)")
        else:
            fk = (fp.x, fp.y)
            tk = ow.tile_at(fp).kind.value
            if fk in ow.mobs:
                lines.append(f"Looking at {tk} (mob: {ow.mobs[fk].kind})")
            else:
                lines.append(f"Looking at {tk}")
    elif dim == "dungeon":
        assert game.mineshaft_run is not None
        run = game.mineshaft_run
        room = run.rooms[run.current_room]
        lines.append(f"Dungeon tier {run.tier}  depth {room.depth}")
        lines.append(f"Room {room.title}")
        lines.append("Looking at — interior (no block grid)")
    elif dim == "nether":
        assert game.nether_world is not None
        nw = game.nether_world
        foot = nw.tile_at(p.pos).kind.value
        lines.append(f"Nether terrain {foot}")
        fp = _forward_cell(p)
        if nw.in_bounds(fp):
            lines.append(f"Looking at {nw.tile_at(fp).kind.value}")
    elif dim == "end":
        assert game.end_world is not None
        ew = game.end_world
        foot = ew.tile_at(p.pos).kind.value
        lines.append(f"End terrain {foot}")
        if game.end_run:
            er = game.end_run
            lines.append(f"Ender Dragon {er.dragon_hp}/{er.dragon_max_hp} HP")
        if game.victory:
            lines.append("Victory — press E to return home")
    return "\n".join(lines)


def _with_forward_highlight(base: Style, is_forward: bool) -> Style:
    if not is_forward:
        return base
    return base + _FORWARD_HI


def _overworld_cell(
    ow: Overworld,
    px: int,
    py: int,
    is_player: bool,
    is_forward_cell: bool,
    *,
    dragon_at: Pos | None = None,
) -> tuple[str, Style]:
    if is_player:
        return "@", _PLAYER

    if not (0 <= px < ow.width and 0 <= py < ow.height):
        return "█", _with_forward_highlight(_OOB, is_forward_cell)

    key = (px, py)
    if dragon_at is not None and px == dragon_at.x and py == dragon_at.y:
        return "D", _with_forward_highlight(_DRAGON, is_forward_cell)

    tg = ow.tiles[py][px].kind

    # Mob overlay
    if key in ow.mobs:
        return "☠", _with_forward_highlight(_MOB, is_forward_cell)

    # Cave entrance — distinct marker
    if tg is TileKind.CAVE_ENTRANCE:
        return "⛏", _with_forward_highlight(_CAVE, is_forward_cell)
    if tg is TileKind.NETHER_PORTAL:
        return "P", _with_forward_highlight(_TERRAIN[TileKind.NETHER_PORTAL], is_forward_cell)
    if tg is TileKind.END_GATE:
        return "E", _with_forward_highlight(_TERRAIN[TileKind.END_GATE], is_forward_cell)

    # Trees — stand out on grass
    if tg is TileKind.TREE:
        return "♣", _with_forward_highlight(_TREE, is_forward_cell)

    # Ores on stone background
    if tg is TileKind.COAL_ORE:
        st = _with_forward_highlight(_ORE_COAL, is_forward_cell)
        return "C", st
    if tg is TileKind.IRON_ORE:
        st = _with_forward_highlight(_ORE_IRON, is_forward_cell)
        return "I", st

    # Plain terrain block (per-kind char + fg/bg for visibility)
    char = _TERRAIN_CHAR.get(tg, "█")
    base = _TERRAIN.get(tg, Style.parse("white on bright_black"))
    st = _with_forward_highlight(base, is_forward_cell)
    return char, st


def render_overworld(
    ow: Overworld,
    player: Player,
    radius_w: int = 10,
    radius_h: int = 10,
    *,
    dragon_at: Pos | None = None,
) -> Text:
    """Colored terrain blocks; gatherables use distinct glyphs; forward mining cell highlighted."""
    forward = _forward_cell(player)
    out = Text()
    for dy in range(-radius_h, radius_h + 1):
        for dx in range(-radius_w, radius_w + 1):
            px, py = player.pos.x + dx, player.pos.y + dy
            is_pl = px == player.pos.x and py == player.pos.y
            is_fc = (px, py) == (forward.x, forward.y) and not is_pl
            ch, st = _overworld_cell(
                ow, px, py, is_pl, is_fc, dragon_at=dragon_at
            )
            out.append(ch, style=st)
        if dy < radius_h:
            out.append("\n")
    return out


def render_mineshaft(run: MineshaftRun) -> str:
    r = run.rooms[run.current_room]
    inner_w = 52
    top = "╔" + "═" * (inner_w - 2) + "╗"
    bot = "╚" + "═" * (inner_w - 2) + "╝"

    def row(s: str) -> str:
        pad = inner_w - 2 - len(s)
        if pad < 0:
            s = s[: inner_w - 2]
            pad = 0
        return "║" + s + " " * pad + "║"

    explored = len(set(run.visited_room_ids) | {run.current_room})
    total_rooms = len(run.rooms)
    body_lines = [
        "Abandoned mineshaft (text crawl — no block grid)",
        "",
        r.title,
        f"Depth: {r.depth}  Tier: {run.tier}  Rooms explored: {explored}/{total_rooms}",
        "",
        "Exits:",
    ]
    for direction, dest in sorted(r.exits.items()):
        body_lines.append(f"  {direction:5} → {run.rooms[dest].title}")
    body_lines.append("")
    if r.exit_to_overworld:
        body_lines.append("[E] Climb ladder to the Overworld")
    if r.mob_kind and r.mob_hp > 0:
        body_lines.append(f"Threat: {r.mob_kind} HP {r.mob_hp}")
    elif r.loot_id and not r.loot_taken:
        body_lines.append(f"Salvage: {item_name(r.loot_id)}")
    framed = [top] + [row(line) for line in body_lines] + [bot]
    return "\n".join(framed)


def render_sidebar(game, show_debug: bool = False) -> str:
    p = game.player
    inv = p.inventory.counts
    biome = ""
    if game.victory:
        biome = "   Victory!"
    elif game.dimension == "overworld":
        b = game.overworld.biome_at(p.pos)
        biome = f"   {b.name.lower()}"
    elif game.dimension == "dungeon" and game.mineshaft_run:
        biome = f"   Dungeon tier {game.mineshaft_run.tier}"
    elif game.dimension == "nether":
        biome = "   Nether"
    elif game.dimension == "end":
        biome = "   The End"
    top = [
        f"Seed {game.seed}   {game.dimension}  GM:{game.mc_game_mode}{biome}",
        "",
        "Inventory:",
    ]
    if not inv:
        top.append("  (empty)")
    else:
        for k in sorted(inv):
            top.append(f"  {item_name(k)} x{inv[k]}")
    out = "\n".join(top)
    if show_debug:
        out = out + "\n\n" + format_debug_overlay(game)
    return out
