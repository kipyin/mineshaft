from __future__ import annotations

from mineshaft.domain.dungeon import DungeonInstance
from mineshaft.domain.items import item_name
from mineshaft.domain.overworld import Overworld
from mineshaft.domain.pos import Pos
from mineshaft.domain.tiles import tile_glyph


def render_overworld(ow: Overworld, player: Pos, radius: int = 10) -> str:
    lines: list[str] = []
    for dy in range(-radius, radius + 1):
        row: list[str] = []
        for dx in range(-radius, radius + 1):
            px, py = player.x + dx, player.y + dy
            if px == player.x and py == player.y:
                row.append("@")
                continue
            if not (0 <= px < ow.width and 0 <= py < ow.height):
                row.append("#")
                continue
            pos = Pos(px, py)
            key = (px, py)
            if key in ow.mobs:
                row.append("M")
                continue
            tg = ow.tile_at(pos).kind
            row.append(tile_glyph(tg))
        lines.append("".join(row))
    return "\n".join(lines)


def render_dungeon(di: DungeonInstance) -> str:
    r = di.rooms[di.current_room]
    lines = [
        r.title,
        f"Depth: {r.depth}  Tier: {di.tier}",
        "",
        "Exits:",
    ]
    for direction, dest in sorted(r.exits.items()):
        lines.append(f"  {direction:5} → {di.rooms[dest].title}")
    lines.append("")
    if r.exit_to_overworld:
        lines.append("[E] Use ladder out (press E)")
    if r.mob_kind and r.mob_hp > 0:
        lines.append(f"Threat: {r.mob_kind} HP {r.mob_hp}")
    elif r.loot_id and not r.loot_taken:
        lines.append(f"Salvage: {r.loot_id}")
    return "\n".join(lines)


def render_sidebar(game) -> str:
    p = game.player
    inv = p.inventory.counts
    biome = ""
    if game.mode == "overworld":
        b = game.overworld.biome_at(p.pos)
        biome = f"   Biome {b.name.lower()}"
    elif game.dungeon:
        biome = f"   Dungeon tier {game.dungeon.tier}"
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
    return "\n".join(top)
