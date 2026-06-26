from __future__ import annotations

import pytest
from pydantic import ValidationError

from biome_lab.config.defaults import create_default_preset
from biome_lab.config.schemas import CreatureTraits


def test_default_preset_is_valid() -> None:
    preset = create_default_preset()

    assert preset.simulation.initial_herbivores > 0
    assert preset.herbivore.role == "herbivore"
    assert preset.predator.role == "predator"
    assert preset.herbivore.reproduction_threshold > preset.herbivore.hunger_threshold


def test_invalid_energy_thresholds_are_rejected() -> None:
    preset = create_default_preset()
    data = preset.herbivore.model_dump()
    data["hunger_threshold"] = data["max_energy"]

    with pytest.raises(ValidationError):
        CreatureTraits.model_validate(data)


def test_invalid_terrain_palette_is_rejected() -> None:
    data = create_default_preset().model_dump()
    data["simulation"]["topology"]["palette"] = "unknown"

    with pytest.raises(ValidationError):
        type(create_default_preset()).model_validate(data)
