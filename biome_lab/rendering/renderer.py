from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np
import pygame

from biome_lab.entities.creatures import Creature
from biome_lab.rendering import colors
from biome_lab.rendering.overlays import draw_vision_cone


class Renderer:
    VISION_OVERLAY_LIMIT = 180
    STATE_TEXT_LIMIT = 90

    def __init__(self, font: pygame.font.Font, small_font: pygame.font.Font) -> None:
        self.font = font
        self.small_font = small_font
        self.world_rect = pygame.Rect(0, 0, 1, 1)
        self.scale = 1.0
        self.offset = np.zeros(2, dtype=float)
        self._state_label_cache: Dict[Tuple[str, Tuple[int, int, int]], pygame.Surface] = {}

    def configure_view(self, rect: pygame.Rect, world_width: float, world_height: float) -> None:
        self.world_rect = rect
        self.scale = min(rect.width / world_width, rect.height / world_height)
        used_width = world_width * self.scale
        used_height = world_height * self.scale
        self.offset = np.array(
            [
                rect.x + (rect.width - used_width) / 2.0,
                rect.y + (rect.height - used_height) / 2.0,
            ],
            dtype=float,
        )

    def world_to_screen(self, position: np.ndarray) -> Tuple[int, int]:
        point = self.offset + position * self.scale
        return int(point[0]), int(point[1])

    def screen_to_world(self, position: Tuple[int, int]) -> np.ndarray:
        point = (np.array(position, dtype=float) - self.offset) / max(self.scale, 1e-8)
        return point

    def draw(
        self,
        surface: pygame.Surface,
        world,
        rect: pygame.Rect,
        show_vision: bool,
        show_states: bool,
        selected_id: Optional[int],
    ) -> None:
        self.configure_view(rect, world.config.world_width, world.config.world_height)
        pygame.draw.rect(surface, colors.WORLD_BG, rect)
        self._draw_grid(surface, world)
        clipped = surface.get_clip()
        surface.set_clip(rect)
        living_count = world.living_creature_count()
        if show_vision:
            self._draw_vision(surface, world, selected_id)
        self._draw_plants(surface, world)
        self._draw_creatures(surface, world.herbivores, selected_id, show_states, living_count)
        self._draw_creatures(surface, world.predators, selected_id, show_states, living_count)
        surface.set_clip(clipped)
        pygame.draw.rect(surface, colors.PANEL_BORDER, rect, 1)

    def _draw_grid(self, surface: pygame.Surface, world) -> None:
        step = 100
        for x in range(0, world.config.world_width + step, step):
            sx = int(self.offset[0] + x * self.scale)
            start = (sx, int(self.offset[1]))
            end = (sx, int(self.offset[1] + world.config.world_height * self.scale))
            pygame.draw.line(surface, colors.WORLD_GRID, start, end, 1)
        for y in range(0, world.config.world_height + step, step):
            sy = int(self.offset[1] + y * self.scale)
            start = (int(self.offset[0]), sy)
            end = (int(self.offset[0] + world.config.world_width * self.scale), sy)
            pygame.draw.line(surface, colors.WORLD_GRID, start, end, 1)

    def _draw_plants(self, surface: pygame.Surface, world) -> None:
        radius = max(2, int(world.config.plant.radius * self.scale))
        for plant in world.plants:
            if not plant.alive:
                continue
            pygame.draw.circle(surface, colors.PLANT, self.world_to_screen(plant.position), radius)

    def _draw_creatures(
        self,
        surface: pygame.Surface,
        creatures,
        selected_id: Optional[int],
        show_states: bool,
        living_count: int,
    ) -> None:
        draw_state_text = living_count <= self.STATE_TEXT_LIMIT
        for creature in creatures:
            if not creature.alive or creature.traits is None:
                continue
            center = self.world_to_screen(creature.position)
            radius = max(5, int(creature.radius * self.scale))
            self._draw_oriented_triangle(surface, creature, center, radius)
            if selected_id == creature.id:
                pygame.draw.circle(surface, colors.SELECTION, center, radius + 5, 2)
            if show_states:
                state_color = colors.BEHAVIOR_COLORS.get(creature.behavior.value, colors.TEXT_MUTED)
                if draw_state_text or selected_id == creature.id:
                    label = self._state_label(creature.behavior.value, state_color)
                    surface.blit(label, (center[0] + radius + 3, center[1] - radius - 2))
                else:
                    pygame.draw.circle(surface, state_color, (center[0], center[1] - radius - 4), 3)

    def _state_label(self, value: str, color: Tuple[int, int, int]) -> pygame.Surface:
        key = (value, color)
        label = self._state_label_cache.get(key)
        if label is None:
            label = self.small_font.render(value.replace("_", " "), True, color)
            self._state_label_cache[key] = label
        return label

    def _draw_oriented_triangle(
        self,
        surface: pygame.Surface,
        creature: Creature,
        center: Tuple[int, int],
        radius: int,
    ) -> None:
        heading = creature.heading
        if float(np.linalg.norm(heading)) < 1e-8:
            heading = np.array([1.0, 0.0], dtype=float)
        heading = heading / max(float(np.linalg.norm(heading)), 1e-8)
        perpendicular = np.array([-heading[1], heading[0]])
        center_vec = np.array(center, dtype=float)
        nose = center_vec + heading * radius * 1.8
        left = center_vec - heading * radius * 0.9 + perpendicular * radius
        right = center_vec - heading * radius * 0.9 - perpendicular * radius
        points = [(int(nose[0]), int(nose[1])), (int(left[0]), int(left[1])), (int(right[0]), int(right[1]))]
        pygame.draw.polygon(surface, creature.traits.color, points)
        pygame.draw.polygon(surface, (12, 18, 19), points, 1)

    def _draw_vision(self, surface: pygame.Surface, world, selected_id: Optional[int]) -> None:
        creatures = list(world.iter_living_creatures())
        if len(creatures) > self.VISION_OVERLAY_LIMIT:
            step = int(np.ceil(len(creatures) / self.VISION_OVERLAY_LIMIT))
            sampled = creatures[::step]
            if selected_id is not None:
                selected = world.find_creature(selected_id)
                if selected is not None and selected.alive and selected not in sampled:
                    sampled.append(selected)
            creatures = sampled
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for creature in creatures:
            if creature.traits is None:
                continue
            center = self.world_to_screen(creature.position)
            draw_vision_cone(
                overlay,
                center,
                creature.heading,
                creature.traits.vision_range * self.scale,
                creature.traits.vision_angle_deg,
                creature.traits.color,
            )
        surface.blit(overlay, (0, 0))
