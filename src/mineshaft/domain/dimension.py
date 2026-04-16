from __future__ import annotations

from typing import Literal

# Which plane the player occupies. Dungeon is the graph crawl (mineshaft), not a top-down map.
Dimension = Literal["overworld", "dungeon", "nether", "end"]
