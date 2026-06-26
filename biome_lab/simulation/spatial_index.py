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
        cells = self._cells
        cells.clear()
        cell_size = self.cell_size
        for entity in entities:
            if not entity.alive:
                continue
            position = entity.position
            cell = (int(float(position[0]) // cell_size), int(float(position[1]) // cell_size))
            cells[cell].append(entity)

    def query_radius(self, position: np.ndarray, radius: float) -> List[object]:
        return self.query_radius_into(position, radius, [])

    def query_radius_into(
        self,
        position: np.ndarray,
        radius: float,
        results: List[object],
        clear: bool = True,
    ) -> List[object]:
        if clear:
            results.clear()
        cell_size = self.cell_size
        origin_x = float(position[0])
        origin_y = float(position[1])
        min_x = int((origin_x - radius) // cell_size)
        max_x = int((origin_x + radius) // cell_size)
        min_y = int((origin_y - radius) // cell_size)
        max_y = int((origin_y + radius) // cell_size)
        radius_sq = radius * radius
        cells_get = self._cells.get
        append = results.append
        for cell_x in range(min_x, max_x + 1):
            for cell_y in range(min_y, max_y + 1):
                cell_entities = cells_get((cell_x, cell_y))
                if not cell_entities:
                    continue
                for entity in cell_entities:
                    entity_position = entity.position
                    delta_x = float(entity_position[0]) - origin_x
                    delta_y = float(entity_position[1]) - origin_y
                    if delta_x * delta_x + delta_y * delta_y <= radius_sq:
                        append(entity)
        return results

    def _cell_for(self, position: np.ndarray) -> Tuple[int, int]:
        return int(float(position[0]) // self.cell_size), int(float(position[1]) // self.cell_size)
