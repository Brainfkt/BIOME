from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EventKind(str, Enum):
    BIRTH = "birth"
    DEATH = "death"
    FEEDING = "feeding"
    PREDATION = "predation"


class DeathCause(str, Enum):
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
