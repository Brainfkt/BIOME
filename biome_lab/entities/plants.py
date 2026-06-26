from __future__ import annotations

from dataclasses import dataclass

from biome_lab.entities.base import Entity


@dataclass
class Plant(Entity):
    energy: float = 0.0

