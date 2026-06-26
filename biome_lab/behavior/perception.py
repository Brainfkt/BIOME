from __future__ import annotations

import math
from typing import Iterable, List

import numpy as np

from biome_lab.behavior.steering import EPSILON_SQ, length_squared
from biome_lab.entities.creatures import Creature


class PerceptionSystem:
    def visible_entities(self, observer: Creature, candidates: Iterable[object]) -> List[object]:
        return self.visible_entities_into(observer, candidates, [])

    def visible_entities_into(
        self,
        observer: Creature,
        candidates: Iterable[object],
        results: List[object],
        assume_in_range: bool = False,
    ) -> List[object]:
        assert observer.traits is not None
        results.clear()
        observer_id = observer.id
        observer_position = observer.position
        observer_x = float(observer_position[0])
        observer_y = float(observer_position[1])
        vision_range_sq = observer.traits.vision_range * observer.traits.vision_range
        check_angle = observer.traits.vision_angle_deg < 359.0
        heading = observer.heading
        heading_x = float(heading[0])
        heading_y = float(heading[1])
        heading_sq = heading_x * heading_x + heading_y * heading_y
        if heading_sq < EPSILON_SQ:
            check_angle = False
            heading_length = 0.0
            cos_half_angle = 0.0
        elif check_angle:
            heading_length = math.sqrt(heading_sq)
            cos_half_angle = math.cos(math.radians(observer.traits.vision_angle_deg / 2.0))
        else:
            heading_length = 0.0
            cos_half_angle = 0.0

        append = results.append
        for candidate in candidates:
            if not candidate.alive:
                continue
            if candidate.id == observer_id:
                continue
            target_position = candidate.position
            delta_x = float(target_position[0]) - observer_x
            delta_y = float(target_position[1]) - observer_y
            if assume_in_range and not check_angle:
                append(candidate)
                continue
            distance_sq = delta_x * delta_x + delta_y * delta_y
            if not assume_in_range and distance_sq > vision_range_sq:
                continue
            if distance_sq < EPSILON_SQ or not check_angle:
                append(candidate)
                continue
            dot = delta_x * heading_x + delta_y * heading_y
            if dot >= cos_half_angle * math.sqrt(distance_sq) * heading_length:
                append(candidate)
        return results

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
