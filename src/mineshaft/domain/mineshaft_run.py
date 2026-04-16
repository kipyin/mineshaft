from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MineshaftRoom:
    id: str
    title: str
    depth: int
    exits: dict[str, str]
    mob_kind: str | None
    mob_hp: int
    mob_max_hp: int
    mob_atk: int
    loot_id: str | None
    loot_taken: bool = False
    is_entrance: bool = False
    exit_to_overworld: bool = False
    # Escape shaft: can open End portal with enough Eye of Ender (see engine).
    exit_to_end_portal: bool = False


@dataclass
class MineshaftRun:
    mineshaft_id: str
    tier: int
    rooms: dict[str, MineshaftRoom]
    current_room: str
    entrance_room_id: str
    overworld_return: tuple[int, int]
    visited_room_ids: list[str] = field(default_factory=list)
