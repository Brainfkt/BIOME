from __future__ import annotations

from typing import Tuple

import numpy as np


def create_rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def random_position(
    rng: np.random.Generator,
    width: float,
    height: float,
    padding: float = 0.0,
) -> np.ndarray:
    x = rng.uniform(padding, max(padding, width - padding))
    y = rng.uniform(padding, max(padding, height - padding))
    return np.array([x, y], dtype=float)


def random_unit_vector(rng: np.random.Generator) -> np.ndarray:
    angle = rng.uniform(0.0, np.pi * 2.0)
    return np.array([np.cos(angle), np.sin(angle)], dtype=float)


def jittered_position(
    rng: np.random.Generator,
    center: np.ndarray,
    radius: float,
    bounds: Tuple[float, float],
) -> np.ndarray:
    offset = random_unit_vector(rng) * rng.uniform(0.0, radius)
    position = center + offset
    position[0] = float(np.clip(position[0], 0.0, bounds[0]))
    position[1] = float(np.clip(position[1], 0.0, bounds[1]))
    return position

