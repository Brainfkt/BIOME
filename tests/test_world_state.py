from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError

from biome_lab.config.defaults import create_default_preset
from biome_lab.config.schemas import BiomeLabPreset, DiseaseState, WorldState
from biome_lab.simulation.world import World


def _empty_preset() -> BiomeLabPreset:
    data = create_default_preset().model_dump()
    data["simulation"]["initial_herbivores"] = 0
    data["simulation"]["initial_predators"] = 0
    data["simulation"]["plant"]["initial_count"] = 0
    data["simulation"]["disease"]["enabled"] = False
    data["simulation"]["disease"]["initial_infected"] = 0
    return BiomeLabPreset.model_validate(data)


def test_world_state_round_trip_preserves_sandbox_state(tmp_path) -> None:
    world = World(_empty_preset())
    world.time = 12.5
    world._plant_regrowth_credit = 0.75
    world.spawn_plant(np.array([90.0, 120.0]))
    herbivore = world.spawn_creature("herbivore", np.array([200.0, 220.0]), initial=True)
    assert herbivore is not None
    herbivore.energy = 77.0
    herbivore.age = 8.0
    herbivore.infect()
    herbivore.recover()
    herbivore.generation = 2
    herbivore.mutation_count = 1
    world.add_obstacle_rect(np.array([420.0, 260.0]), width=60.0, height=40.0)
    world.apply_topology_brush(np.array([300.0, 300.0]), radius=90.0, strength=0.2, mode="ridge")
    world.set_system_enabled("seasons", True)
    world.set_system_enabled("disease", True)
    world.set_system_enabled("mutation", True)

    path = tmp_path / "state.json"
    world.to_world_state().save_json(path)
    loaded_state = WorldState.from_json_path(path)
    loaded = World.from_world_state(loaded_state)

    assert loaded_state.document_type == "world_state"
    assert loaded_state.schema_version == 1
    assert loaded.time == pytest.approx(world.time)
    assert loaded._plant_regrowth_credit == pytest.approx(world._plant_regrowth_credit)
    assert len(loaded.plants) == len(world.plants)
    assert loaded.creature_counts() == world.creature_counts()
    assert len(loaded.obstacles) == len(world.obstacles)
    assert loaded.config.topology.enabled
    assert loaded.config.seasons.enabled
    assert loaded.config.disease.enabled
    assert loaded.config.mutation.enabled
    assert np.allclose(loaded.topology_grid, world.topology_grid)
    assert loaded_state.model_dump(mode="json")["creatures"][0]["disease_state"] == "recovered"
    assert loaded.herbivores[0].energy == pytest.approx(77.0)
    assert loaded.herbivores[0].disease_state == DiseaseState.RECOVERED
    assert loaded.herbivores[0].mutation_count == 1


def test_world_state_rejects_unknown_schema_version() -> None:
    world = World(_empty_preset())
    data = world.to_world_state().model_dump(mode="json")
    data["schema_version"] = 999

    with pytest.raises(ValidationError, match="unsupported world_state schema_version"):
        WorldState.model_validate(data)


def test_world_state_rejects_unknown_disease_state() -> None:
    world = World(_empty_preset())
    creature = world.spawn_creature("herbivore", np.array([200.0, 220.0]), initial=True)
    assert creature is not None
    data = world.to_world_state().model_dump(mode="json")
    data["creatures"][0]["disease_state"] = "latent"

    with pytest.raises(ValidationError):
        WorldState.model_validate(data)
