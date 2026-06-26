from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar, Dict, Optional, Tuple

import numpy as np

from biome_lab.config.schemas import CreatureTraits, DiseaseState
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
    DISEASE_TRANSITIONS: ClassVar[Dict[DiseaseState, Tuple[DiseaseState, ...]]] = {
        DiseaseState.SUSCEPTIBLE: (DiseaseState.SUSCEPTIBLE, DiseaseState.INFECTED),
        DiseaseState.INFECTED: (DiseaseState.INFECTED, DiseaseState.RECOVERED),
        DiseaseState.RECOVERED: (DiseaseState.RECOVERED,),
    }

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
    disease_state: DiseaseState = DiseaseState.SUSCEPTIBLE
    infection_timer: float = 0.0
    generation: int = 0
    mutation_count: int = 0

    def __setattr__(self, name: str, value: object) -> None:
        if name == "disease_state":
            new_state = DiseaseState(value)
            current = self.__dict__.get("disease_state")
            if current is not None:
                current_state = DiseaseState(current)
                if new_state not in self.DISEASE_TRANSITIONS[current_state]:
                    raise ValueError(
                        "invalid disease transition: %s -> %s"
                        % (current_state.value, new_state.value)
                    )
            value = new_state
        super().__setattr__(name, value)

    def infect(self) -> None:
        self.disease_state = DiseaseState.INFECTED
        self.infection_timer = 0.0

    def recover(self) -> None:
        self.disease_state = DiseaseState.RECOVERED
        self.infection_timer = 0.0

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

    def register_behavior_time(self, dt: float) -> None:
        key = self.behavior.value
        self.behavior_time[key] = self.behavior_time.get(key, 0.0) + dt

    def mark_dead(self, cause: DeathCause) -> None:
        self.alive = False
        self.death_cause = cause
        self.velocity = np.zeros(2, dtype=float)
