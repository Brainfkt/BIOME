from __future__ import annotations

import math
from typing import Iterable, List

import numpy as np

from biome_lab.behavior.steering import EPSILON_SQ, length_squared
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
        distance_sq = length_squared(delta)
        if distance_sq > observer.traits.vision_range * observer.traits.vision_range:
            return False
        if distance_sq < EPSILON_SQ:
            return True
        if observer.traits.vision_angle_deg >= 359.0:
            return True
        heading_sq = length_squared(observer.heading)
        if heading_sq < EPSILON_SQ:
            return True
        half_angle = math.radians(observer.traits.vision_angle_deg / 2.0)
        threshold = math.cos(half_angle) * math.sqrt(distance_sq * heading_sq)
        return float(np.dot(delta, observer.heading)) >= threshold
