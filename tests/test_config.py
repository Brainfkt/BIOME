from __future__ import annotations

import pytest
from pydantic import ValidationError

from biome_lab.config.defaults import create_default_preset
from biome_lab.config.schemas import BiomeLabPreset, CreatureTraits


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


def test_unsupported_preset_schema_version_is_rejected() -> None:
    data = create_default_preset().model_dump()
    data["schema_version"] = 999

    with pytest.raises(ValidationError, match="unsupported preset schema_version"):
        BiomeLabPreset.model_validate(data)


def test_initial_creatures_cannot_exceed_max_creatures() -> None:
    data = create_default_preset().model_dump()
    data["simulation"]["initial_herbivores"] = 10
    data["simulation"]["initial_predators"] = 5
    data["simulation"]["max_creatures"] = 12

    with pytest.raises(ValidationError, match="initial_herbivores"):
        BiomeLabPreset.model_validate(data)


def test_obstacles_must_fit_inside_world() -> None:
    data = create_default_preset().model_dump()
    data["simulation"]["environment"]["obstacles"] = [
        {
            "name": "bad_wall",
            "x": data["simulation"]["world_width"] - 20,
            "y": 20,
            "width": 80,
            "height": 40,
            "blocks_movement": True,
        }
    ]

    with pytest.raises(ValidationError, match="obstacle"):
        BiomeLabPreset.model_validate(data)


def test_environment_zone_multipliers_are_bounded() -> None:
    data = create_default_preset().model_dump()
    data["simulation"]["environment"]["zones"] = [
        {
            "name": "too_fast",
            "x": 50,
            "y": 50,
            "width": 100,
            "height": 100,
            "color": [70, 106, 124],
            "speed_multiplier": 20,
            "metabolism_multiplier": 1,
            "movement_cost_multiplier": 1,
            "plant_regrowth_multiplier": 1,
            "disease_transmission_multiplier": 1,
        }
    ]

    with pytest.raises(ValidationError):
        BiomeLabPreset.model_validate(data)


def test_topology_feature_center_must_be_inside_world() -> None:
    data = create_default_preset().model_dump()
    data["simulation"]["topology"]["features"][0]["x"] = data["simulation"]["world_width"] + 1

    with pytest.raises(ValidationError, match="topology feature"):
        BiomeLabPreset.model_validate(data)


def test_topology_grid_too_large_for_ui_is_rejected() -> None:
    data = create_default_preset().model_dump()
    data["simulation"]["topology"]["grid_columns"] = 512
    data["simulation"]["topology"]["grid_rows"] = 512

    with pytest.raises(ValidationError, match="topology grid"):
        BiomeLabPreset.model_validate(data)


def test_simulation_and_protocol_seeds_must_match() -> None:
    data = create_default_preset().model_dump()
    data["protocol"]["seed"] = data["simulation"]["seed"] + 1

    with pytest.raises(ValidationError, match="simulation.seed"):
        BiomeLabPreset.model_validate(data)


def test_mutation_rejects_unknown_mutable_trait() -> None:
    data = create_default_preset().model_dump()
    data["simulation"]["mutation"]["mutable_traits"] = ["hunger_threshold"]

    with pytest.raises(ValidationError):
        BiomeLabPreset.model_validate(data)


def test_mutation_requires_bounds_for_mutable_traits() -> None:
    data = create_default_preset().model_dump()
    data["simulation"]["mutation"]["mutable_traits"] = ["max_speed", "vision_range"]
    del data["simulation"]["mutation"]["trait_bounds"]["vision_range"]

    with pytest.raises(ValidationError, match="missing mutation trait bounds"):
        BiomeLabPreset.model_validate(data)


def test_mutation_trait_bounds_must_be_ordered() -> None:
    data = create_default_preset().model_dump()
    data["simulation"]["mutation"]["trait_bounds"]["max_speed"] = {
        "min_value": 100.0,
        "max_value": 50.0,
    }

    with pytest.raises(ValidationError, match="min_value"):
        BiomeLabPreset.model_validate(data)
