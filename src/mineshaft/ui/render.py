from __future__ import annotations

from rich.style import Style
from rich.text import Text

from mineshaft.domain.items import item_name
from mineshaft.domain.mineshaft_run import MineshaftRun
from mineshaft.domain.overworld import Overworld
from mineshaft.domain.player import Player
from mineshaft.domain.pos import Pos
from mineshaft.domain.tiles import TileKind

MC_DAY_TICKS = 24000

# Muted terrain backgrounds (16-color friendly)
_TERRAIN = {
    TileKind.GRASS: Style.parse("on dark_green"),
    TileKind.DIRT: Style.parse("on yellow4"),
    TileKind.STONE: Style.parse("on bright_black"),
    TileKind.SAND: Style.parse("on yellow"),
    TileKind.WATER: Style.parse("on blue"),
    TileKind.BEDROCK: Style.parse("white on black"),
}

_ORE_COAL = Style.parse("white on bright_black")
_ORE_IRON = Style.parse("bright_yellow on bright_black")


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
        day_s,
        time_s,
    ]
    if game.mode == "overworld":
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
    else:
        assert game.mineshaft_run is not None
        run = game.mineshaft_run
        room = run.rooms[run.current_room]
        ow = game.overworld
        surf = ow.tile_at(p.pos).kind.value
        sbio = ow.biome_at(p.pos).name.lower()
        lines.append(f"Surface biome (entrance) {sbio}")
        lines.append(f"Terrain (entrance tile) {surf}")
        lines.append(f"Mineshaft tier {run.tier}  depth {room.depth}")
        lines.append(f"Room {room.title}")
        ladder = "yes" if room.exit_to_overworld else "no"
        lines.append(f"Ladder exit {ladder}")
        lines.append("Looking at — interior (no block grid)")
    return "\n".join(lines)


def _with_forward_highlight(base: Style, is_forward: bool) -> Style:
    if not is_forward:
        return base
    return base + Style.parse("reverse bold")


def _overworld_cell(
    ow: Overworld,
    px: int,
    py: int,
    is_player: bool,
    is_forward_cell: bool,
) -> tuple[str, Style]:
    if is_player:
        st = Style.parse("bold black on bright_yellow")
        return "@", st

    if not (0 <= px < ow.width and 0 <= py < ow.height):
        st = Style.parse("on black")
        return "█", _with_forward_highlight(st, is_forward_cell)

    key = (px, py)
    tg = ow.tile_at(Pos(px, py)).kind

    # Mob overlay
    if key in ow.mobs:
        char, st = "☠", Style.parse("bold bright_red on dark_red")
        return char, _with_forward_highlight(st, is_forward_cell)

    # Cave entrance — distinct marker
    if tg is TileKind.CAVE_ENTRANCE:
        char, st = "⛏", Style.parse("bold bright_black on magenta")
        return char, _with_forward_highlight(st, is_forward_cell)

    # Trees — stand out on grass
    if tg is TileKind.TREE:
        char, st = "♣", Style.parse("bold green on dark_green")
        return char, _with_forward_highlight(st, is_forward_cell)

    # Ores on stone background
    if tg is TileKind.COAL_ORE:
        st = _with_forward_highlight(_ORE_COAL, is_forward_cell)
        return "C", st
    if tg is TileKind.IRON_ORE:
        st = _with_forward_highlight(_ORE_IRON, is_forward_cell)
        return "I", st

    # Plain terrain block
    char = "█"
    base = _TERRAIN.get(tg, Style.parse("on bright_black"))
    if tg is TileKind.WATER:
        char = "~"
    st = _with_forward_highlight(base, is_forward_cell)
    return char, st


def render_overworld(
    ow: Overworld,
    player: Player,
    radius_w: int = 10,
    radius_h: int = 10,
) -> Text:
    """Colored terrain blocks; gatherables use distinct glyphs; forward mining cell highlighted."""
    forward = _forward_cell(player)
    out = Text()
    for dy in range(-radius_h, radius_h + 1):
        for dx in range(-radius_w, radius_w + 1):
            px, py = player.pos.x + dx, player.pos.y + dy
            is_pl = px == player.pos.x and py == player.pos.y
            is_fc = (px, py) == (forward.x, forward.y) and not is_pl
            ch, st = _overworld_cell(ow, px, py, is_pl, is_fc)
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
        body_lines.append("[E] Climb ladder to surface (press E)")
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
    if game.mode == "overworld":
        b = game.overworld.biome_at(p.pos)
        biome = f"   {b.name.lower()}"
    elif game.mineshaft_run:
        biome = f"   Abandoned mineshaft tier {game.mineshaft_run.tier}"
    top = [
        f"HP {p.hp}/{p.max_hp}   Food {p.hunger}/{p.max_hunger}",
        f"Seed {game.seed}   Mode {game.mode}{biome}",
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
