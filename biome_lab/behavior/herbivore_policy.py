from __future__ import annotations

from typing import Iterable, List

import numpy as np

from biome_lab.behavior.decision import BehaviorDecision
from biome_lab.behavior.steering import flee_from, seek, wander
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
        threats = [
            predator
            for predator in visible_predators
            if herbivore.distance_to(predator) <= herbivore.traits.flee_distance
        ]
        if threats:
            return BehaviorDecision(
                state=BehaviorState.FLEEING,
                desired_velocity=flee_from(herbivore.position, threats, herbivore.traits.max_speed),
                target_id=getattr(threats[0], "id", None),
            )

        plants: List[object] = list(visible_plants)
        if herbivore.is_hungry() and plants:
            target = min(plants, key=herbivore.distance_to)
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

