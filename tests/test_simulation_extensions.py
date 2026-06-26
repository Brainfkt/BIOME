from __future__ import annotations

import numpy as np
import pytest

from biome_lab.config.defaults import create_default_preset
from biome_lab.config.schemas import BiomeLabPreset, DiseaseState, ObstacleConfig
from biome_lab.simulation.engine import SimulationEngine
from biome_lab.simulation.events import DeathCause, EventKind
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
    source.infect()
    world.refresh_indices()

    events = world.update(0.1)

    assert target.disease_state == DiseaseState.INFECTED
    assert any(event.kind.value == "infection" for event in events)


def test_living_creature_count_tracks_spawns_deaths_and_loads() -> None:
    preset = _preset_with_updates(
        lambda data: data["simulation"].update(
            {
                "initial_herbivores": 0,
                "initial_predators": 0,
                "plant": {
                    **data["simulation"]["plant"],
                    "initial_count": 0,
                },
            }
        )
    )
    world = World(preset)
    first = world.spawn_creature("herbivore", np.array([100.0, 100.0]), initial=True)
    second = world.spawn_creature("predator", np.array([160.0, 100.0]), initial=True)

    assert first is not None
    assert second is not None
    assert world.living_creature_count() == 2

    world._kill_creature(first, DeathCause.FAMINE)
    assert world.living_creature_count() == 1
    world._remove_dead()
    assert world.creature_counts() == {"herbivore": 0, "predator": 1}

    loaded = World.from_world_state(world.to_world_state())
    assert loaded.living_creature_count() == 1


def test_ui_engine_keeps_full_metrics_for_large_presets() -> None:
    preset = _preset_with_updates(
        lambda data: data["simulation"].update(
            {
                "initial_herbivores": 0,
                "initial_predators": 0,
                "max_creatures": 2500,
            }
        )
    )

    engine = SimulationEngine(preset)

    assert engine.metrics.mode == "full"


def test_disease_state_transitions_are_strict() -> None:
    world = World(create_default_preset())
    creature = world.herbivores[0]

    with pytest.raises(ValueError, match="invalid disease transition"):
        creature.recover()

    assert creature.disease_state == DiseaseState.SUSCEPTIBLE
    creature.infect()
    assert creature.disease_state == DiseaseState.INFECTED
    creature.recover()
    assert creature.disease_state == DiseaseState.RECOVERED
    with pytest.raises(ValueError, match="invalid disease transition"):
        creature.infect()


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
                    "mutable_traits": ["max_speed"],
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
    mutation_events = [event for event in events if event.kind == EventKind.MUTATION]
    assert len(mutation_events) == 1
    assert mutation_events[0].entity_id == child.id
    assert mutation_events[0].target_id == parent.id
    assert mutation_events[0].mutation_trait == "max_speed"
    assert mutation_events[0].old_value != mutation_events[0].new_value


def test_mutation_respects_trait_bounds() -> None:
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
                    "strength": 1.0,
                    "mutable_traits": ["max_speed"],
                    "trait_bounds": {
                        **data["simulation"]["mutation"]["trait_bounds"],
                        "max_speed": {
                            "min_value": 70.0,
                            "max_value": 71.0,
                        },
                    },
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
    mutation_event = next(event for event in events if event.kind == EventKind.MUTATION)

    assert 70.0 <= child.traits.max_speed <= 71.0
    assert mutation_event.new_value == child.traits.max_speed


def test_invalid_trait_mutation_is_refused_without_mutating_child() -> None:
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
                    "strength": 1.0,
                    "min_trait_multiplier": 0.1,
                    "max_trait_multiplier": 4.0,
                    "mutable_traits": ["reproduction_cost"],
                    "trait_bounds": {
                        **data["simulation"]["mutation"]["trait_bounds"],
                        "reproduction_cost": {
                            "min_value": 95.0,
                            "max_value": 100.0,
                        },
                    },
                },
            }
        )
    )
    world = World(preset)
    parent = world.spawn_creature("herbivore", np.array([200.0, 200.0]), initial=True)
    parent.traits = parent.traits.model_copy(update={"reproduction_cost": 91.0})
    parent.energy = parent.traits.reproduction_threshold
    parent.reproduction_cooldown_remaining = 0.0

    events = world._try_reproduce(parent)
    child = world.herbivores[-1]

    assert child.mutation_count == 0
    assert child.traits.reproduction_cost == 91.0
    assert not any(event.kind == EventKind.MUTATION for event in events)


def test_mutation_is_reproducible_with_fixed_seed() -> None:
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
                    "strength": 0.25,
                    "mutable_traits": ["vision_range"],
                },
            }
        )
    )
    mutation_events = []
    for _ in range(2):
        world = World(preset)
        parent = world.spawn_creature("herbivore", np.array([200.0, 200.0]), initial=True)
        parent.energy = parent.traits.reproduction_threshold
        parent.reproduction_cooldown_remaining = 0.0
        events = world._try_reproduce(parent)
        mutation_events.append(next(event for event in events if event.kind == EventKind.MUTATION))

    assert mutation_events[0].mutation_trait == mutation_events[1].mutation_trait
    assert mutation_events[0].new_value == mutation_events[1].new_value


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

    topology_events = world.set_system_enabled("topology", True)
    world.set_system_enabled("seasons", True)
    world.set_system_enabled("mutation", True)
    disease_events = world.set_system_enabled("disease", True, preferred_id=creature.id)

    assert world.config.topology.enabled
    assert world.config.seasons.enabled
    assert world.config.mutation.enabled
    assert world.config.disease.enabled
    assert creature.disease_state == DiseaseState.INFECTED
    assert topology_events[0].kind == EventKind.SYSTEM_TOGGLE
    assert any(event.kind == EventKind.INITIAL_INFECTION for event in disease_events)


def test_boundary_bounce_changes_velocity_after_collision() -> None:
    world = World(create_default_preset())
    old_position = np.array([2.0, 100.0])
    new_position = np.array([-4.0, 100.0])
    velocity = np.array([-60.0, 0.0])

    bounded, adjusted_velocity = world._apply_bounds(old_position, new_position, velocity, dt=0.1)

    assert bounded[0] == 0.0
    assert adjusted_velocity[0] == 60.0 * world.config.boundary_bounce


def test_sandbox_spawn_rejects_obstacle_and_out_of_bounds_positions() -> None:
    world = World(create_default_preset())
    obstacle = world.add_obstacle_rect(np.array([300.0, 300.0]), width=100.0, height=100.0)
    center = np.array([obstacle.x + obstacle.width / 2.0, obstacle.y + obstacle.height / 2.0])

    assert world.spawn_plant(center) is None
    assert "blocked" in (world.last_spawn_error or "")
    assert world.spawn_creature("herbivore", np.array([-10.0, 50.0]), initial=True) is None
    assert "outside" in (world.last_spawn_error or "")


def test_random_free_position_returns_none_when_world_is_blocked() -> None:
    world = World(create_default_preset())
    world.obstacles = [
        ObstacleConfig(
            name="full_block",
            x=0.0,
            y=0.0,
            width=float(world.config.world_width),
            height=float(world.config.world_height),
            blocks_movement=True,
        )
    ]

    assert world._random_free_position(world.config.herbivore_radius) is None


def test_initial_infections_create_events_on_reset() -> None:
    preset = _preset_with_updates(
        lambda data: data["simulation"].update(
            {
                "disease": {
                    **data["simulation"]["disease"],
                    "enabled": True,
                    "initial_infected": 2,
                },
            }
        )
    )

    world = World(preset)

    assert sum(event.kind == EventKind.INITIAL_INFECTION for event in world.events) == 2
