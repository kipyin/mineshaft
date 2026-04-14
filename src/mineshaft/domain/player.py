from __future__ import annotations

from dataclasses import dataclass, field

from mineshaft.domain.direction import Direction
from mineshaft.domain.inventory import Inventory
from mineshaft.domain.pos import Pos


@dataclass
class Player:
    pos: Pos
    facing: Direction
    hp: int = 20
    max_hp: int = 20
    hunger: int = 20
    max_hunger: int = 20
    inventory: Inventory = field(default_factory=Inventory)
