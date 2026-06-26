from __future__ import annotations

import math
from typing import Tuple

import pygame


def draw_vision_cone(
    surface: pygame.Surface,
    center: Tuple[int, int],
    heading,
    radius: float,
    angle_deg: float,
    color: Tuple[int, int, int],
    alpha: int = 26,
) -> None:
    if radius <= 0:
        return
    angle = math.atan2(float(heading[1]), float(heading[0]))
    half = math.radians(angle_deg / 2.0)
    steps = max(6, int(angle_deg // 18))
    points = [center]
    for index in range(steps + 1):
        t = -half + (2.0 * half * index / steps)
        px = center[0] + math.cos(angle + t) * radius
        py = center[1] + math.sin(angle + t) * radius
        points.append((int(px), int(py)))
    pygame.draw.polygon(surface, (color[0], color[1], color[2], alpha), points)
    pygame.draw.lines(surface, (color[0], color[1], color[2], min(alpha * 3, 120)), False, points, 1)
