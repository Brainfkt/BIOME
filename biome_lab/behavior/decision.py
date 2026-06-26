from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from biome_lab.entities.creatures import BehaviorState


@dataclass
class BehaviorDecision:
    state: BehaviorState
    desired_velocity: np.ndarray
    target_id: Optional[int] = None
    should_reproduce: bool = False

