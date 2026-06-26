from __future__ import annotations

from typing import Iterable, List

import numpy as np

from biome_lab.behavior.decision import BehaviorDecision
from biome_lab.behavior.steering import distance_squared, flee_from, seek, wander
from biome_lab.entities.creatures import BehaviorState
from biome_lab.entities.herbivores import Herbivore


class HerbivorePolicy:
    def decide(
        self,
        herbivore: Herbivore,
        visible_predators: Iterable[object],
        visible_plants: Iterable[object],
        rng: np.random.Generator,
    ) -> BehaviorDecision:
        assert herbivore.traits is not None
        flee_distance_sq = herbivore.traits.flee_distance * herbivore.traits.flee_distance
        threats = [
            predator
            for predator in visible_predators
            if distance_squared(herbivore.position, getattr(predator, "position")) <= flee_distance_sq
        ]
        if threats:
            return BehaviorDecision(
                state=BehaviorState.FLEEING,
                desired_velocity=flee_from(herbivore.position, threats, herbivore.traits.max_speed),
                target_id=getattr(threats[0], "id", None),
            )

        plants: List[object] = list(visible_plants)
        if herbivore.is_hungry() and plants:
            target = min(plants, key=lambda plant: distance_squared(herbivore.position, getattr(plant, "position")))
            return BehaviorDecision(
                state=BehaviorState.SEEKING_FOOD,
                desired_velocity=seek(herbivore.position, getattr(target, "position"), herbivore.traits.max_speed),
                target_id=getattr(target, "id", None),
            )

        if herbivore.can_reproduce():
            return BehaviorDecision(
                state=BehaviorState.REPRODUCING,
                desired_velocity=np.zeros(2, dtype=float),
                should_reproduce=True,
            )

        return BehaviorDecision(
            state=BehaviorState.EXPLORING,
            desired_velocity=wander(herbivore.heading, rng, herbivore.traits.max_speed),
        )
