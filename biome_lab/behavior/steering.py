from __future__ import annotations

import math
from typing import Iterable

import numpy as np


EPSILON = 1e-8
EPSILON_SQ = EPSILON * EPSILON


def length_squared(vector: np.ndarray) -> float:
    x = float(vector[0])
    y = float(vector[1])
    return x * x + y * y


def distance_squared(first: np.ndarray, second: np.ndarray) -> float:
    delta_x = float(first[0]) - float(second[0])
    delta_y = float(first[1]) - float(second[1])
    return delta_x * delta_x + delta_y * delta_y


def length(vector: np.ndarray) -> float:
    return math.sqrt(length_squared(vector))


def normalize_with_length(vector: np.ndarray) -> tuple[np.ndarray, float]:
    x = float(vector[0])
    y = float(vector[1])
    magnitude_sq = x * x + y * y
    if magnitude_sq < EPSILON_SQ:
        return np.zeros(2, dtype=float), 0.0
    magnitude = math.sqrt(magnitude_sq)
    return np.array([x / magnitude, y / magnitude], dtype=float), magnitude


def normalize(vector: np.ndarray) -> np.ndarray:
    x = float(vector[0])
    y = float(vector[1])
    magnitude_sq = x * x + y * y
    if magnitude_sq < EPSILON_SQ:
        return np.zeros(2, dtype=float)
    magnitude = math.sqrt(magnitude_sq)
    return np.array([x / magnitude, y / magnitude], dtype=float)


def clamp_magnitude(vector: np.ndarray, max_length: float) -> np.ndarray:
    x = float(vector[0])
    y = float(vector[1])
    magnitude_sq = x * x + y * y
    max_length_sq = max_length * max_length
    if magnitude_sq <= max_length_sq or magnitude_sq < EPSILON_SQ:
        return vector
    magnitude = math.sqrt(magnitude_sq)
    scale = max_length / magnitude
    return np.array([x * scale, y * scale], dtype=float)


def seek(current: np.ndarray, target: np.ndarray, max_speed: float) -> np.ndarray:
    delta_x = float(target[0]) - float(current[0])
    delta_y = float(target[1]) - float(current[1])
    distance_sq = delta_x * delta_x + delta_y * delta_y
    if distance_sq < EPSILON_SQ:
        return np.zeros(2, dtype=float)
    scale = max_speed / math.sqrt(distance_sq)
    return np.array([delta_x * scale, delta_y * scale], dtype=float)


def flee_from(current: np.ndarray, threats: Iterable[object], max_speed: float) -> np.ndarray:
    current_x = float(current[0])
    current_y = float(current[1])
    combined_x = 0.0
    combined_y = 0.0
    for threat in threats:
        threat_position = getattr(threat, "position")
        delta_x = current_x - float(threat_position[0])
        delta_y = current_y - float(threat_position[1])
        distance_sq = max(delta_x * delta_x + delta_y * delta_y, EPSILON_SQ)
        distance = math.sqrt(distance_sq)
        scale = 1.0 / (distance * distance_sq)
        combined_x += delta_x * scale
        combined_y += delta_y * scale
    magnitude_sq = combined_x * combined_x + combined_y * combined_y
    if magnitude_sq < EPSILON_SQ:
        return np.zeros(2, dtype=float)
    scale = max_speed / math.sqrt(magnitude_sq)
    return np.array([combined_x * scale, combined_y * scale], dtype=float)


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
