from __future__ import annotations

from typing import Iterable, List

import numpy as np

from biome_lab.behavior.decision import BehaviorDecision
from biome_lab.behavior.steering import distance_squared, seek, wander
from biome_lab.entities.creatures import BehaviorState
from biome_lab.entities.predators import Predator


class PredatorPolicy:
    def decide(
        self,
        predator: Predator,
        visible_prey: Iterable[object],
        rng: np.random.Generator,
    ) -> BehaviorDecision:
        assert predator.traits is not None
        prey: List[object] = list(visible_prey)
        if prey:
            target = min(prey, key=lambda candidate: distance_squared(predator.position, getattr(candidate, "position")))
            close_distance = predator.traits.attack_range + predator.traits.max_speed
            if predator.is_hungry() or distance_squared(predator.position, getattr(target, "position")) <= close_distance * close_distance:
                return BehaviorDecision(
                    state=BehaviorState.HUNTING,
                    desired_velocity=seek(predator.position, getattr(target, "position"), predator.traits.max_speed),
                    target_id=getattr(target, "id", None),
                )

        if predator.can_reproduce():
            return BehaviorDecision(
                state=BehaviorState.REPRODUCING,
                desired_velocity=np.zeros(2, dtype=float),
                should_reproduce=True,
            )

        return BehaviorDecision(
            state=BehaviorState.EXPLORING,
            desired_velocity=wander(predator.heading, rng, predator.traits.max_speed),
        )
