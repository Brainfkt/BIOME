from __future__ import annotations

import pygame

from biome_lab.rendering import colors
from biome_lab.ui.panels import draw_key_value, draw_panel, draw_wrapped


def draw_inspector(
    surface: pygame.Surface,
    rect: pygame.Rect,
    title_font: pygame.font.Font,
    small_font: pygame.font.Font,
    creature,
) -> None:
    body = draw_panel(surface, rect, "Inspection scientifique", title_font)
    y = body.y
    if creature is None:
        draw_wrapped(surface, "Aucune creature selectionnee.", small_font, colors.TEXT_MUTED, body.x, y, body.width)
        return
    traits = creature.traits
    if traits is None:
        return
    y = draw_key_value(surface, small_font, "ID", creature.id, body.x, y, body.width)
    y = draw_key_value(surface, small_font, "Espece", traits.name, body.x, y, body.width)
    y = draw_key_value(surface, small_font, "Role", traits.role, body.x, y, body.width)
    y = draw_key_value(surface, small_font, "Energie", "%.1f / %.1f" % (creature.energy, traits.max_energy), body.x, y, body.width)
    y = draw_key_value(surface, small_font, "Age", "%.1f / %.1f s" % (creature.age, traits.max_age), body.x, y, body.width)
    y = draw_key_value(surface, small_font, "Comportement", creature.behavior.value, body.x, y, body.width)
    y = draw_key_value(surface, small_font, "Sante", creature.disease_state.value, body.x, y, body.width)
    y = draw_key_value(surface, small_font, "Generation", creature.generation, body.x, y, body.width)
    y = draw_key_value(surface, small_font, "Mutations", creature.mutation_count, body.x, y, body.width)
    y = draw_key_value(surface, small_font, "Cooldown repro", "%.1f s" % creature.reproduction_cooldown_remaining, body.x, y, body.width)
    y += 8
    card = traits.science_card
    sections = [
        ("Role ecologique", card.ecological_role),
        ("Traits morphologiques", "; ".join(card.morphological_traits)),
        ("Traits sensoriels", "; ".join(card.sensory_traits)),
        ("Traits energetiques", "; ".join(card.energetic_traits)),
        ("Traits reproductifs", "; ".join(card.reproductive_traits)),
        ("Regles", "; ".join(card.behavioral_rules)),
        ("Justification", "; ".join(card.rule_justification)),
    ]
    for title, text in sections:
        if y > body.bottom - 40:
            break
        surface.blit(small_font.render(title, True, colors.ACCENT), (body.x, y))
        y += small_font.get_height() + 2
        y = draw_wrapped(surface, text, small_font, colors.TEXT_MUTED, body.x, y, body.width)
        y += 4
