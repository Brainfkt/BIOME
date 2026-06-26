from __future__ import annotations

from typing import Iterable, List

import numpy as np

from biome_lab.behavior.steering import EPSILON, normalize
from biome_lab.entities.creatures import Creature


class PerceptionSystem:
    def visible_entities(self, observer: Creature, candidates: Iterable[object]) -> List[object]:
        assert observer.traits is not None
        visible: List[object] = []
        for candidate in candidates:
            if not getattr(candidate, "alive", True):
                continue
            if getattr(candidate, "id", None) == observer.id:
                continue
            if self.is_visible(observer, getattr(candidate, "position")):
                visible.append(candidate)
        return visible

    def is_visible(self, observer: Creature, target_position: np.ndarray) -> bool:
        assert observer.traits is not None
        delta = target_position - observer.position
        distance = float(np.linalg.norm(delta))
        if distance > observer.traits.vision_range:
            return False
        if distance < EPSILON:
            return True
        if observer.traits.vision_angle_deg >= 359.0:
            return True
        direction = normalize(delta)
        heading = normalize(observer.heading)
        if float(np.linalg.norm(heading)) < EPSILON:
            return True
        half_angle = np.deg2rad(observer.traits.vision_angle_deg / 2.0)
        return float(np.dot(direction, heading)) >= float(np.cos(half_angle))

