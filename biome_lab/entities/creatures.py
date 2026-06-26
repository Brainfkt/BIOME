from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

import numpy as np

from biome_lab.config.schemas import CreatureTraits
from biome_lab.entities.base import Entity
from biome_lab.simulation.events import DeathCause


class BehaviorState(str, Enum):
    FLEEING = "fleeing"
    SEEKING_FOOD = "seeking_food"
    HUNTING = "hunting"
    REPRODUCING = "reproducing"
    EXPLORING = "exploring"
    IDLE = "idle"


@dataclass
class Creature(Entity):
    traits: Optional[CreatureTraits] = None
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(2, dtype=float))
    heading: np.ndarray = field(default_factory=lambda: np.array([1.0, 0.0], dtype=float))
    energy: float = 0.0
    age: float = 0.0
    birth_time: float = 0.0
    reproduction_cooldown_remaining: float = 0.0
    behavior: BehaviorState = BehaviorState.EXPLORING
    target_id: Optional[int] = None
    death_cause: Optional[DeathCause] = None
    behavior_time: Dict[str, float] = field(default_factory=dict)

    def is_hungry(self) -> bool:
        assert self.traits is not None
        return self.energy <= self.traits.hunger_threshold

    def can_reproduce(self) -> bool:
        assert self.traits is not None
        return (
            self.alive
            and self.energy >= self.traits.reproduction_threshold
            and self.reproduction_cooldown_remaining <= 0.0
        )

    def clamp_energy(self) -> None:
        assert self.traits is not None
        self.energy = float(np.clip(self.energy, 0.0, self.traits.max_energy))

    def apply_energy_cost(self, distance: float, dt: float) -> None:
        assert self.traits is not None
        self.energy -= self.traits.basal_metabolism * dt
        self.energy -= self.traits.movement_energy_cost * distance

    def register_behavior_time(self, dt: float) -> None:
        key = self.behavior.value
        self.behavior_time[key] = self.behavior_time.get(key, 0.0) + dt

    def mark_dead(self, cause: DeathCause) -> None:
        self.alive = False
        self.death_cause = cause
        self.velocity = np.zeros(2, dtype=float)

