from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EventKind(str, Enum):
    BIRTH = "birth"
    DEATH = "death"
    FEEDING = "feeding"
    INITIAL_INFECTION = "initial_infection"
    INFECTION = "infection"
    SYSTEM_TOGGLE = "system_toggle"
    PREDATION = "predation"
    RECOVERY = "recovery"


class DeathCause(str, Enum):
    DISEASE = "disease"
    FAMINE = "famine"
    PREDATION = "predation"
    OLD_AGE = "old_age"


@dataclass
class SimulationEvent:
    time: float
    kind: EventKind
    species: str
    entity_id: int
    target_id: Optional[int] = None
    cause: Optional[DeathCause] = None
    energy: Optional[float] = None
    age: Optional[float] = None
    generation: Optional[int] = None
    mutation_count: Optional[int] = None
    system: Optional[str] = None
    enabled: Optional[bool] = None
