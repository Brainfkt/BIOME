from __future__ import annotations

import numpy as np

from biome_lab.behavior.herbivore_policy import HerbivorePolicy
from biome_lab.behavior.perception import PerceptionSystem
from biome_lab.behavior.predator_policy import PredatorPolicy
from biome_lab.config.defaults import create_default_preset
from biome_lab.entities.creatures import BehaviorState
from biome_lab.entities.herbivores import Herbivore
from biome_lab.entities.plants import Plant
from biome_lab.entities.predators import Predator
from biome_lab.simulation.world import MAX_CREATURE_TURN_RATE, World


def _observer(vision_range: float = 60.0, vision_angle_deg: float = 90.0) -> Herbivore:
    preset = create_default_preset()
    traits = preset.herbivore.model_copy(
        update={
            "vision_range": vision_range,
            "vision_angle_deg": vision_angle_deg,
        }
    )
    return Herbivore(
        id=1,
        position=np.array([100.0, 100.0]),
        radius=6.0,
        kind="herbivore",
        traits=traits,
        heading=np.array([1.0, 0.0], dtype=float),
        energy=traits.max_energy,
    )


def test_perception_rejects_targets_outside_range() -> None:
    observer = _observer(vision_range=30.0)

    assert not PerceptionSystem().is_visible(observer, np.array([131.0, 100.0]))


def test_perception_accepts_same_position_target() -> None:
    observer = _observer()

    assert PerceptionSystem().is_visible(observer, observer.position.copy())


def test_perception_respects_vision_angle() -> None:
    observer = _observer(vision_range=80.0, vision_angle_deg=60.0)

    assert PerceptionSystem().is_visible(observer, np.array([140.0, 100.0]))
    assert not PerceptionSystem().is_visible(observer, np.array([100.0, 140.0]))


def test_perception_allows_omnidirectional_vision() -> None:
    observer = _observer(vision_range=80.0, vision_angle_deg=360.0)

    assert PerceptionSystem().is_visible(observer, np.array([60.0, 100.0]))


def test_visible_entities_into_reuses_result_buffer() -> None:
    observer = _observer(vision_range=80.0, vision_angle_deg=90.0)
    visible = Plant(id=2, position=np.array([120.0, 100.0]), radius=4.0, kind="plant", energy=20.0)
    outside_angle = Plant(id=3, position=np.array([100.0, 120.0]), radius=4.0, kind="plant", energy=20.0)
    outside_range = Plant(id=4, position=np.array([220.0, 100.0]), radius=4.0, kind="plant", energy=20.0)
    results = [outside_range]

    returned = PerceptionSystem().visible_entities_into(
        observer,
        [visible, outside_angle, outside_range],
        results,
    )

    assert returned is results
    assert results == [visible]


def test_herbivore_fleeing_has_priority_over_food_and_reproduction() -> None:
    preset = create_default_preset()
    herbivore = Herbivore(
        id=1,
        position=np.array([100.0, 100.0]),
        radius=6.0,
        kind="herbivore",
        traits=preset.herbivore,
        energy=preset.herbivore.max_energy,
    )
    predator = Predator(
        id=2,
        position=np.array([120.0, 100.0]),
        radius=7.5,
        kind="predator",
        traits=preset.predator,
        energy=80.0,
    )
    plant = Plant(id=3, position=np.array([90.0, 100.0]), radius=4.0, kind="plant", energy=22.0)

    decision = HerbivorePolicy().decide(
        herbivore,
        visible_predators=[predator],
        visible_plants=[plant],
        rng=np.random.default_rng(1),
    )

    assert decision.state == BehaviorState.FLEEING


def test_predator_hunts_when_hungry_and_prey_visible() -> None:
    preset = create_default_preset()
    predator = Predator(
        id=1,
        position=np.array([100.0, 100.0]),
        radius=7.5,
        kind="predator",
        traits=preset.predator,
        energy=preset.predator.hunger_threshold - 1.0,
    )
    prey = Herbivore(
        id=2,
        position=np.array([150.0, 100.0]),
        radius=6.0,
        kind="herbivore",
        traits=preset.herbivore,
        energy=80.0,
    )

    decision = PredatorPolicy().decide(predator, visible_prey=[prey], rng=np.random.default_rng(1))

    assert decision.state == BehaviorState.HUNTING
    assert decision.target_id == prey.id


def test_creature_turning_is_smoothed_over_time() -> None:
    preset = create_default_preset()
    world = World(preset)
    creature = world.herbivores[0]
    assert creature.traits is not None
    creature.position = np.array([500.0, 500.0])
    creature.heading = np.array([1.0, 0.0], dtype=float)
    creature.velocity = np.array([creature.traits.max_speed, 0.0], dtype=float)

    dt = 1.0 / 30.0
    desired_velocity = np.array([-creature.traits.max_speed, 0.0], dtype=float)

    world._move_and_charge_energy(creature, desired_velocity, dt)

    angle = float(np.arccos(np.clip(np.dot(creature.heading, np.array([1.0, 0.0])), -1.0, 1.0)))
    assert angle <= MAX_CREATURE_TURN_RATE * dt + 1e-6
    assert creature.heading[0] > 0.0
