from __future__ import annotations

from typing import Iterable

import numpy as np


EPSILON = 1e-8


def length(vector: np.ndarray) -> float:
    return float(np.linalg.norm(vector))


def normalize(vector: np.ndarray) -> np.ndarray:
    magnitude = length(vector)
    if magnitude < EPSILON:
        return np.zeros(2, dtype=float)
    return vector / magnitude


def clamp_magnitude(vector: np.ndarray, max_length: float) -> np.ndarray:
    magnitude = length(vector)
    if magnitude <= max_length or magnitude < EPSILON:
        return vector
    return vector / magnitude * max_length


def seek(current: np.ndarray, target: np.ndarray, max_speed: float) -> np.ndarray:
    return normalize(target - current) * max_speed


def flee_from(current: np.ndarray, threats: Iterable[object], max_speed: float) -> np.ndarray:
    combined = np.zeros(2, dtype=float)
    for threat in threats:
        delta = current - getattr(threat, "position")
        distance_sq = max(float(np.dot(delta, delta)), EPSILON)
        combined += normalize(delta) / distance_sq
    direction = normalize(combined)
    if length(direction) < EPSILON:
        return np.zeros(2, dtype=float)
    return direction * max_speed


def wander(
    heading: np.ndarray,
    rng: np.random.Generator,
    max_speed: float,
    jitter: float = 0.55,
) -> np.ndarray:
    noise = rng.normal(0.0, 1.0, size=2)
    direction = normalize(heading + noise * jitter)
    if length(direction) < EPSILON:
        angle = rng.uniform(0.0, np.pi * 2.0)
        direction = np.array([np.cos(angle), np.sin(angle)], dtype=float)
    return direction * max_speed

