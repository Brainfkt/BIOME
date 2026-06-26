from __future__ import annotations

import numpy as np

from biome_lab.config.defaults import create_default_preset
from biome_lab.config.schemas import BiomeLabPreset
from biome_lab.simulation.world import World


def _preset_with_updates(updates) -> BiomeLabPreset:
    data = create_default_preset().model_dump()
    updates(data)
    return BiomeLabPreset.model_validate(data)


def test_disease_transmits_by_proximity_when_enabled() -> None:
    preset = _preset_with_updates(
        lambda data: (
            data["simulation"].update(
                {
                    "initial_herbivores": 0,
                    "initial_predators": 0,
                    "plant": {
                        **data["simulation"]["plant"],
                        "initial_count": 0,
                    },
                    "disease": {
                        **data["simulation"]["disease"],
                        "enabled": True,
                        "transmission_radius": 50.0,
                        "transmission_probability_per_second": 100.0,
                        "energy_drain_per_second": 0.0,
                    },
                }
            )
        )
    )
    world = World(preset)
    source = world.spawn_creature("herbivore", np.array([100.0, 100.0]), initial=True)
    target = world.spawn_creature("herbivore", np.array([110.0, 100.0]), initial=True)
    source.disease_state = "infected"
    world.refresh_indices()

    events = world.update(0.1)

    assert target.disease_state == "infected"
    assert any(event.kind.value == "infection" for event in events)


def test_mutation_marks_child_generation_when_enabled() -> None:
    preset = _preset_with_updates(
        lambda data: data["simulation"].update(
            {
                "initial_herbivores": 0,
                "initial_predators": 0,
                "plant": {
                    **data["simulation"]["plant"],
                    "initial_count": 0,
                },
                "mutation": {
                    **data["simulation"]["mutation"],
                    "enabled": True,
                    "probability": 1.0,
                    "strength": 0.05,
                },
            }
        )
    )
    world = World(preset)
    parent = world.spawn_creature("herbivore", np.array([200.0, 200.0]), initial=True)
    parent.energy = parent.traits.reproduction_threshold
    parent.reproduction_cooldown_remaining = 0.0

    events = world._try_reproduce(parent)
    child = world.herbivores[-1]

    assert events
    assert child.generation == 1
    assert child.mutation_count == 1


def test_sandbox_obstacles_can_be_added_and_removed() -> None:
    world = World(create_default_preset())
    center = np.array([300.0, 300.0])

    world.add_obstacle_rect(center, width=80.0, height=40.0)

    assert world._position_blocked(center, 1.0)
    assert world.remove_entity_at(center)
    assert not world._position_blocked(center, 1.0)


def test_enabled_season_reports_active_phase() -> None:
    preset = _preset_with_updates(lambda data: data["simulation"]["seasons"].update({"enabled": True}))
    world = World(preset)

    assert world.current_season_index() == 0
    assert world.current_season_name() == "printemps"


def test_topology_feature_can_generate_a_valley() -> None:
    preset = _preset_with_updates(lambda data: data["simulation"]["topology"].update({"enabled": True}))
    world = World(preset)

    valley_center = np.array([560.0, 380.0])

    assert world.topology_enabled()
    assert world.sample_elevation(valley_center) < preset.simulation.topology.base_elevation


def test_sandbox_topology_brush_carves_and_exports_relief() -> None:
    world = World(create_default_preset())
    center = np.array([280.0, 220.0])
    before = world.sample_elevation(center)
    world.config.topology.palette = "hydrology"

    world.apply_topology_brush(center, radius=80.0, strength=0.2, mode="valley")
    after = world.sample_elevation(center)
    state = world.to_state_dict()

    assert world.topology_enabled()
    assert after < before
    assert "topology" in state
    assert state["topology"]["palette"] == "hydrology"
    assert state["topology"]["summary"]["min_elevation"] <= after


def test_runtime_settings_toggle_experimental_systems() -> None:
    world = World(create_default_preset())
    creature = world.herbivores[0]

    world.set_system_enabled("topology", True)
    world.set_system_enabled("seasons", True)
    world.set_system_enabled("mutation", True)
    world.set_system_enabled("disease", True, preferred_id=creature.id)

    assert world.config.topology.enabled
    assert world.config.seasons.enabled
    assert world.config.mutation.enabled
    assert world.config.disease.enabled
    assert creature.disease_state == "infected"
