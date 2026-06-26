from __future__ import annotations

from typing import Dict, List, Tuple

import pygame

from biome_lab.config.parameter_docs import PARAMETER_DOCS
from biome_lab.metrics.definitions import METRIC_DEFINITIONS
from biome_lab.rendering import colors


def draw_panel(surface: pygame.Surface, rect: pygame.Rect, title: str, font: pygame.font.Font) -> pygame.Rect:
    pygame.draw.rect(surface, colors.PANEL_BG, rect)
    pygame.draw.rect(surface, colors.PANEL_BORDER, rect, 1)
    title_surf = font.render(title, True, colors.TEXT)
    surface.blit(title_surf, (rect.x + 14, rect.y + 10))
    return pygame.Rect(rect.x + 14, rect.y + 38, rect.width - 28, rect.height - 48)


def draw_wrapped(
    surface: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    color: Tuple[int, int, int],
    x: int,
    y: int,
    width: int,
    line_gap: int = 3,
) -> int:
    words = text.split()
    line = ""
    for word in words:
        candidate = word if not line else line + " " + word
        if font.size(candidate)[0] <= width:
            line = candidate
        else:
            if line:
                surface.blit(font.render(line, True, color), (x, y))
                y += font.get_height() + line_gap
            line = word
    if line:
        surface.blit(font.render(line, True, color), (x, y))
        y += font.get_height() + line_gap
    return y


def draw_key_value(
    surface: pygame.Surface,
    font: pygame.font.Font,
    key: str,
    value: object,
    x: int,
    y: int,
    width: int,
) -> int:
    label = "%s: %s" % (key, value)
    return draw_wrapped(surface, label, font, colors.TEXT, x, y, width)


def draw_species_config(
    surface: pygame.Surface,
    rect: pygame.Rect,
    title_font: pygame.font.Font,
    small_font: pygame.font.Font,
    preset,
) -> None:
    body = draw_panel(surface, rect, "Configuration des especes", title_font)
    y = body.y
    for traits in (preset.herbivore, preset.predator):
        heading = small_font.render(traits.name, True, traits.color)
        surface.blit(heading, (body.x, y))
        y += small_font.get_height() + 4
        fields = [
            "max_speed",
            "vision_range",
            "vision_angle_deg",
            "basal_metabolism",
            "movement_energy_cost",
            "max_energy",
            "hunger_threshold",
            "reproduction_threshold",
            "reproduction_cost",
            "max_age",
            "flee_distance" if traits.role == "herbivore" else "attack_range",
            "food_energy_gain",
        ]
        for field in fields:
            value = getattr(traits, field)
            y = draw_key_value(surface, small_font, field, round(value, 2), body.x, y, body.width)
            if y > body.bottom - 30:
                return
        y += 8
    y += 6
    definition = PARAMETER_DOCS["hunger_threshold"]["definition"]
    draw_wrapped(surface, definition, small_font, colors.TEXT_MUTED, body.x, y, body.width)


def draw_stats_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    title_font: pygame.font.Font,
    small_font: pygame.font.Font,
    latest: Dict[str, float],
) -> None:
    body = draw_panel(surface, rect, "Statistiques scientifiques", title_font)
    y = body.y
    if not latest:
        draw_wrapped(surface, "Aucune serie temporelle disponible.", small_font, colors.TEXT_MUTED, body.x, y, body.width)
        return
    rows = [
        ("Temps", "%.1f s" % latest.get("time", 0.0)),
        ("Plantes", int(latest.get("population_plants", 0.0))),
        ("Herbivores", int(latest.get("population_herbivores", 0.0))),
        ("Predateurs", int(latest.get("population_predators", 0.0))),
        ("Energie herbivores", "%.1f" % latest.get("mean_energy_herbivores", 0.0)),
        ("Energie predateurs", "%.1f" % latest.get("mean_energy_predators", 0.0)),
        ("Predation/s", "%.3f" % latest.get("predation_rate_window", 0.0)),
        ("Reproduction H/s", "%.3f" % latest.get("reproduction_rate_herbivores_window", 0.0)),
        ("Reproduction P/s", "%.3f" % latest.get("reproduction_rate_predators_window", 0.0)),
        ("Morts famine", int(latest.get("deaths_famine_total", 0.0))),
        ("Morts predation", int(latest.get("deaths_predation_total", 0.0))),
        ("Morts vieillesse", int(latest.get("deaths_old_age_total", 0.0))),
    ]
    for key, value in rows:
        y = draw_key_value(surface, small_font, key, value, body.x, y, body.width)
    y += 4
    definition = METRIC_DEFINITIONS["predation_rate"]
    draw_wrapped(surface, definition.definition, small_font, colors.TEXT_MUTED, body.x, y, body.width)


def draw_death_chart_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    title_font: pygame.font.Font,
    small_font: pygame.font.Font,
    metrics,
    mode: str,
) -> None:
    title = "Mortalite et populations"
    body = draw_panel(surface, rect, title, title_font)
    if mode == "species":
        raw_counts = metrics.death_counts_by_species()
        rows = [
            ("Herbivores", raw_counts.get("herbivore", 0), (60, 185, 120)),
            ("Predateurs", raw_counts.get("predator", 0), (220, 86, 76)),
        ]
        definition = "Nombre cumule de morts par type de creature."
    else:
        raw_counts = metrics.death_counts_by_cause()
        rows = [
            ("Predation", raw_counts.get("predation", 0), colors.HUNTING),
            ("Famine", raw_counts.get("famine", 0), colors.FLEEING),
            ("Vieillesse", raw_counts.get("old_age", 0), colors.TEXT_MUTED),
        ]
        definition = "Nombre cumule de morts par mecanisme ecologique."

    y = body.y
    y = draw_wrapped(surface, "Barres: %s" % definition, small_font, colors.TEXT_MUTED, body.x, y, body.width)
    y += 4

    bar_rect = pygame.Rect(body.x, y, body.width, max(88, int(body.height * 0.34)))
    _draw_death_bars(surface, bar_rect, small_font, rows)
    y = bar_rect.bottom + 12

    line_title = small_font.render("Courbes: population vivante par espece", True, colors.TEXT)
    surface.blit(line_title, (body.x, y))
    y += small_font.get_height() + 6
    if body.bottom - y < 70:
        y = max(body.y, body.bottom - 70)
    line_rect = pygame.Rect(body.x, y, body.width, max(40, body.bottom - y))
    _draw_population_curves(surface, line_rect, small_font, metrics.rows)


def _draw_death_bars(
    surface: pygame.Surface,
    rect: pygame.Rect,
    small_font: pygame.font.Font,
    rows: List[Tuple[str, int, Tuple[int, int, int]]],
) -> None:
    pygame.draw.rect(surface, (23, 29, 31), rect)
    pygame.draw.rect(surface, colors.PANEL_BORDER, rect, 1)

    total = sum(count for _, count, _ in rows)
    max_count = max([count for _, count, _ in rows] + [1])
    bar_gap = 18
    bar_h = max(16, min(28, (rect.height - bar_gap * (len(rows) + 1)) // max(len(rows), 1)))
    bar_x = rect.x + 88
    bar_w = max(20, rect.width - 118)
    bar_y = rect.y + 12
    for label, count, color in rows:
        label_surf = small_font.render(label, True, colors.TEXT)
        surface.blit(label_surf, (rect.x + 12, bar_y + 2))
        pygame.draw.rect(surface, colors.BUTTON, pygame.Rect(bar_x, bar_y, bar_w, bar_h), border_radius=4)
        filled_w = int(bar_w * (count / max_count))
        if filled_w > 0:
            pygame.draw.rect(surface, color, pygame.Rect(bar_x, bar_y, filled_w, bar_h), border_radius=4)
        value = "%s" % count
        value_surf = small_font.render(value, True, colors.TEXT)
        surface.blit(value_surf, (bar_x + bar_w - value_surf.get_width() - 8, bar_y + 2))
        share = 0.0 if total <= 0 else count / total * 100.0
        share_surf = small_font.render("%.1f%%" % share, True, colors.TEXT_MUTED)
        surface.blit(share_surf, (bar_x, bar_y + bar_h + 2))
        bar_y += bar_h + bar_gap


def _draw_population_curves(
    surface: pygame.Surface,
    rect: pygame.Rect,
    small_font: pygame.font.Font,
    rows: List[Dict[str, float]],
) -> None:
    pygame.draw.rect(surface, (23, 29, 31), rect)
    pygame.draw.rect(surface, colors.PANEL_BORDER, rect, 1)

    series = [
        ("Plantes", "population_plants", colors.PLANT),
        ("Herbivores", "population_herbivores", (60, 185, 120)),
        ("Predateurs", "population_predators", (220, 86, 76)),
    ]
    if not rows:
        draw_wrapped(
            surface,
            "Aucun point de population disponible.",
            small_font,
            colors.TEXT_MUTED,
            rect.x + 12,
            rect.y + 12,
            rect.width - 24,
        )
        return

    visible_rows = rows[-120:]
    values = [float(row.get(field, 0.0)) for row in visible_rows for _, field, _ in series]
    max_value = max(values + [1.0])
    plot = pygame.Rect(rect.x + 34, rect.y + 18, max(20, rect.width - 52), max(40, rect.height - 54))

    for index in range(4):
        y = plot.y + int(plot.height * index / 3)
        pygame.draw.line(surface, colors.WORLD_GRID, (plot.x, y), (plot.right, y), 1)
    pygame.draw.rect(surface, colors.PANEL_BORDER, plot, 1)

    max_label = small_font.render("%d" % int(max_value), True, colors.TEXT_MUTED)
    surface.blit(max_label, (rect.x + 8, plot.y - 2))
    zero_label = small_font.render("0", True, colors.TEXT_MUTED)
    surface.blit(zero_label, (rect.x + 18, plot.bottom - zero_label.get_height()))

    if len(visible_rows) == 1:
        x_step = 0.0
    else:
        x_step = plot.width / (len(visible_rows) - 1)

    for label, field, color in series:
        points = []
        for index, row in enumerate(visible_rows):
            value = float(row.get(field, 0.0))
            x = plot.x + x_step * index
            y = plot.bottom - (value / max_value) * plot.height
            points.append((int(x), int(y)))
        if len(points) >= 2:
            pygame.draw.lines(surface, color, False, points, 2)
        elif points:
            pygame.draw.circle(surface, color, points[0], 3)

    legend_x = plot.x
    legend_y = plot.bottom + 8
    latest = visible_rows[-1]
    for label, field, color in series:
        pygame.draw.circle(surface, color, (legend_x + 4, legend_y + 6), 4)
        text = "%s %d" % (label, int(latest.get(field, 0.0)))
        label_surf = small_font.render(text, True, colors.TEXT)
        surface.blit(label_surf, (legend_x + 12, legend_y))
        legend_x += label_surf.get_width() + 30


def draw_protocol_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    title_font: pygame.font.Font,
    small_font: pygame.font.Font,
    preset,
) -> None:
    body = draw_panel(surface, rect, "Protocole experimental", title_font)
    y = body.y
    y = draw_wrapped(surface, preset.protocol.research_question, small_font, colors.TEXT, body.x, y, body.width)
    y += 6
    y = draw_wrapped(surface, "Hypothese: %s" % preset.protocol.hypothesis, small_font, colors.TEXT_MUTED, body.x, y, body.width)
    y += 6
    y = draw_wrapped(surface, "VI: %s" % preset.protocol.independent_variable, small_font, colors.TEXT, body.x, y, body.width)
    y += 4
    draw_wrapped(
        surface,
        "VD: %s" % ", ".join(preset.protocol.dependent_variables),
        small_font,
        colors.TEXT_MUTED,
        body.x,
        y,
        body.width,
    )
