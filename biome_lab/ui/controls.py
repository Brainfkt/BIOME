from __future__ import annotations

from typing import Callable, Tuple

import pygame

from biome_lab.rendering import colors


class Button:
    def __init__(self, rect: pygame.Rect, label: str, callback: Callable[[], None]) -> None:
        self.rect = rect
        self.label = label
        self.callback = callback

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        mouse_pos = pygame.mouse.get_pos()
        base = colors.BUTTON_HOVER if self.rect.collidepoint(mouse_pos) else colors.BUTTON
        pygame.draw.rect(surface, base, self.rect, border_radius=6)
        pygame.draw.rect(surface, colors.PANEL_BORDER, self.rect, 1, border_radius=6)
        text = font.render(self.label, True, colors.TEXT)
        surface.blit(text, text.get_rect(center=self.rect.center))

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.callback()
            return True
        return False


class ToggleButton(Button):
    def __init__(
        self,
        rect: pygame.Rect,
        label: str,
        getter: Callable[[], bool],
        callback: Callable[[], None],
    ) -> None:
        super().__init__(rect, label, callback)
        self.getter = getter

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        base = colors.BUTTON_ACTIVE if self.getter() else colors.BUTTON
        if self.rect.collidepoint(pygame.mouse.get_pos()):
            base = colors.BUTTON_HOVER if not self.getter() else colors.ACCENT
        pygame.draw.rect(surface, base, self.rect, border_radius=6)
        pygame.draw.rect(surface, colors.PANEL_BORDER, self.rect, 1, border_radius=6)
        text = font.render(self.label, True, colors.TEXT)
        surface.blit(text, text.get_rect(center=self.rect.center))


def control_rects(start_x: int, y: int, labels: Tuple[str, ...], height: int = 36):
    x = start_x
    for label in labels:
        width = max(84, len(label) * 9 + 24)
        yield label, pygame.Rect(x, y, width, height)
        x += width + 10

