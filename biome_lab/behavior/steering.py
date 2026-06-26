from __future__ import annotations

from typing import Iterable

import numpy as np


EPSILON = 1e-8
EPSILON_SQ = EPSILON * EPSILON


def length_squared(vector: np.ndarray) -> float:
    return float(np.dot(vector, vector))


def distance_squared(first: np.ndarray, second: np.ndarray) -> float:
    delta_x = float(first[0]) - float(second[0])
    delta_y = float(first[1]) - float(second[1])
    return delta_x * delta_x + delta_y * delta_y


def length(vector: np.ndarray) -> float:
    return float(np.sqrt(length_squared(vector)))


def normalize_with_length(vector: np.ndarray) -> tuple[np.ndarray, float]:
    magnitude_sq = length_squared(vector)
    if magnitude_sq < EPSILON_SQ:
        return np.zeros(2, dtype=float), 0.0
    magnitude = float(np.sqrt(magnitude_sq))
    return vector / magnitude, magnitude


def normalize(vector: np.ndarray) -> np.ndarray:
    direction, _ = normalize_with_length(vector)
    return direction


def clamp_magnitude(vector: np.ndarray, max_length: float) -> np.ndarray:
    magnitude_sq = length_squared(vector)
    max_length_sq = max_length * max_length
    if magnitude_sq <= max_length_sq or magnitude_sq < EPSILON_SQ:
        return vector
    magnitude = float(np.sqrt(magnitude_sq))
    return vector / magnitude * max_length


def seek(current: np.ndarray, target: np.ndarray, max_speed: float) -> np.ndarray:
    return normalize(target - current) * max_speed


def flee_from(current: np.ndarray, threats: Iterable[object], max_speed: float) -> np.ndarray:
    combined = np.zeros(2, dtype=float)
    for threat in threats:
        delta = current - getattr(threat, "position")
        distance_sq = max(length_squared(delta), EPSILON_SQ)
        distance = float(np.sqrt(distance_sq))
        combined += delta / (distance * distance_sq)
    direction, magnitude = normalize_with_length(combined)
    if magnitude < EPSILON:
        return np.zeros(2, dtype=float)
    return direction * max_speed


def wander(
    heading: np.ndarray,
    rng: np.random.Generator,
    max_speed: float,
    jitter: float = 0.55,
) -> np.ndarray:
    noise = rng.normal(0.0, 1.0, size=2)
    direction, magnitude = normalize_with_length(heading + noise * jitter)
    if magnitude < EPSILON:
        angle = rng.uniform(0.0, np.pi * 2.0)
        direction = np.array([np.cos(angle), np.sin(angle)], dtype=float)
    return direction * max_speed
