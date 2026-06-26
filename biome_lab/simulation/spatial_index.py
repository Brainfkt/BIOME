from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict, Iterable, List, Tuple

import numpy as np


class SpatialIndex:
    """Uniform grid used to keep perception queries cheap and explicit."""

    def __init__(self, cell_size: float) -> None:
        self.cell_size = max(1.0, float(cell_size))
        self._cells: DefaultDict[Tuple[int, int], List[object]] = defaultdict(list)

    def rebuild(self, entities: Iterable[object]) -> None:
        self._cells.clear()
        for entity in entities:
            if not getattr(entity, "alive", True):
                continue
            position = getattr(entity, "position")
            cell = self._cell_for(position)
            self._cells[cell].append(entity)

    def query_radius(self, position: np.ndarray, radius: float) -> List[object]:
        min_x = int((position[0] - radius) // self.cell_size)
        max_x = int((position[0] + radius) // self.cell_size)
        min_y = int((position[1] - radius) // self.cell_size)
        max_y = int((position[1] + radius) // self.cell_size)
        radius_sq = radius * radius
        results: List[object] = []
        for cell_x in range(min_x, max_x + 1):
            for cell_y in range(min_y, max_y + 1):
                for entity in self._cells.get((cell_x, cell_y), []):
                    delta = getattr(entity, "position") - position
                    if float(np.dot(delta, delta)) <= radius_sq:
                        results.append(entity)
        return results

    def _cell_for(self, position: np.ndarray) -> Tuple[int, int]:
        return int(position[0] // self.cell_size), int(position[1] // self.cell_size)
