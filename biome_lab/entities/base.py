from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Entity:
    id: int
    position: np.ndarray
    radius: float
    kind: str = "entity"
    alive: bool = True

    def distance_to(self, other: "Entity") -> float:
        return self.distance_to_position(other.position)

    def distance_to_position(self, position: np.ndarray) -> float:
        return float(np.linalg.norm(self.position - position))

