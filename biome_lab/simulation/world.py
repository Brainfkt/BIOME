from __future__ import annotations

from typing import Dict, Iterator, List, Optional, Sequence

import numpy as np

from biome_lab.behavior.herbivore_policy import HerbivorePolicy
from biome_lab.behavior.perception import PerceptionSystem
from biome_lab.behavior.predator_policy import PredatorPolicy
from biome_lab.behavior.steering import EPSILON, clamp_magnitude, length, normalize
from biome_lab.config.schemas import BiomeLabPreset, CreatureTraits
from biome_lab.entities.creatures import Creature
from biome_lab.entities.herbivores import Herbivore
from biome_lab.entities.plants import Plant
from biome_lab.entities.predators import Predator
from biome_lab.simulation.events import DeathCause, EventKind, SimulationEvent
from biome_lab.simulation.rng import create_rng, jittered_position, random_position, random_unit_vector
from biome_lab.simulation.spatial_index import SpatialIndex


MAX_CREATURE_TURN_RATE = float(np.deg2rad(220.0))


class World:
    def __init__(self, preset: BiomeLabPreset) -> None:
        self.preset = preset
        self.config = preset.simulation
        self.rng = create_rng(self.config.seed)
        self.time = 0.0
        self._id_counter = 0
        self._plant_regrowth_credit = 0.0
        self.plants: List[Plant] = []
        self.herbivores: List[Herbivore] = []
        self.predators: List[Predator] = []
        self.events: List[SimulationEvent] = []
        self.perception = PerceptionSystem()
        self.herbivore_policy = HerbivorePolicy()
        self.predator_policy = PredatorPolicy()
        self.plant_index = SpatialIndex(cell_size=max(self.preset.herbivore.vision_range, 64.0))
        self.herbivore_index = SpatialIndex(cell_size=max(self.preset.predator.vision_range, 64.0))
        self.predator_index = SpatialIndex(cell_size=max(self.preset.herbivore.vision_range, 64.0))
        self.reset()

    @property
    def bounds(self) -> np.ndarray:
        return np.array([self.config.world_width, self.config.world_height], dtype=float)

    def reset(self) -> None:
        self.rng = create_rng(self.config.seed)
        self.time = 0.0
        self._id_counter = 0
        self._plant_regrowth_credit = 0.0
        self.plants = []
        self.herbivores = []
        self.predators = []
        self.events = []
        for _ in range(self.config.plant.initial_count):
            self.spawn_plant()
        for _ in range(self.config.initial_herbivores):
            self.spawn_creature("herbivore", initial=True)
        for _ in range(self.config.initial_predators):
            self.spawn_creature("predator", initial=True)
        self._refresh_indices()

    def next_id(self) -> int:
        self._id_counter += 1
        return self._id_counter

    def all_creatures(self) -> List[Creature]:
        return list(self.herbivores) + list(self.predators)

    def iter_creatures(self) -> Iterator[Creature]:
        yield from self.herbivores
        yield from self.predators

    def iter_living_creatures(self) -> Iterator[Creature]:
        for creature in self.iter_creatures():
            if creature.alive:
                yield creature

    def living_creatures(self) -> List[Creature]:
        return list(self.iter_living_creatures())

    def living_creature_count(self) -> int:
        return sum(1 for creature in self.iter_creatures() if creature.alive)

    def creature_counts(self) -> Dict[str, int]:
        return {
            "herbivore": sum(1 for creature in self.herbivores if creature.alive),
            "predator": sum(1 for creature in self.predators if creature.alive),
        }

    def find_creature(self, entity_id: int) -> Optional[Creature]:
        for creature in self.iter_creatures():
            if creature.id == entity_id:
                return creature
        return None

    def spawn_plant(self, position: Optional[np.ndarray] = None) -> Plant:
        if position is None:
            position = random_position(
                self.rng,
                self.config.world_width,
                self.config.world_height,
                padding=self.config.plant.radius,
            )
        plant = Plant(
            id=self.next_id(),
            position=position,
            radius=self.config.plant.radius,
            kind="plant",
            energy=self.config.plant.energy,
        )
        self.plants.append(plant)
        return plant

    def spawn_creature(
        self,
        species: str,
        position: Optional[np.ndarray] = None,
        initial: bool = False,
        initial_energy: Optional[float] = None,
    ) -> Creature:
        traits = self.preset.herbivore if species == "herbivore" else self.preset.predator
        radius = 6.0 if species == "herbivore" else 7.5
        if position is None:
            position = random_position(self.rng, self.config.world_width, self.config.world_height, padding=radius)
        if initial_energy is None:
            low = traits.max_energy * (0.55 if initial else 0.35)
            high = traits.max_energy * (0.88 if initial else 0.55)
            initial_energy = float(self.rng.uniform(low, high))
        kwargs = {
            "id": self.next_id(),
            "position": position,
            "radius": radius,
            "kind": species,
            "traits": traits,
            "heading": random_unit_vector(self.rng),
            "energy": min(initial_energy, traits.max_energy),
            "birth_time": self.time,
            "reproduction_cooldown_remaining": traits.reproduction_cooldown if not initial else self.rng.uniform(0, traits.reproduction_cooldown),
        }
        if species == "herbivore":
            creature: Creature = Herbivore(**kwargs)
            self.herbivores.append(creature)
        else:
            creature = Predator(**kwargs)
            self.predators.append(creature)
        return creature

    def update(self, dt: float) -> List[SimulationEvent]:
        dt = max(0.0, min(float(dt), 0.25))
        if dt <= 0.0:
            return []
        self.time += dt
        events: List[SimulationEvent] = []
        events.extend(self._age_and_check_mortality(dt))
        self._refresh_indices()

        initial_herbivore_count = len(self.herbivores)
        for index in range(initial_herbivore_count):
            herbivore = self.herbivores[index]
            if herbivore.alive:
                events.extend(self._update_herbivore(herbivore, dt))
        self._refresh_indices(plants=False, predators=False)

        initial_predator_count = len(self.predators)
        for index in range(initial_predator_count):
            predator = self.predators[index]
            if predator.alive:
                events.extend(self._update_predator(predator, dt))

        self._regrow_plants(dt)
        self._remove_dead()
        self.events.extend(events)
        return events

    def _age_and_check_mortality(self, dt: float) -> List[SimulationEvent]:
        events: List[SimulationEvent] = []
        for creature in self.iter_creatures():
            if not creature.alive:
                continue
            assert creature.traits is not None
            creature.age += dt
            creature.reproduction_cooldown_remaining = max(0.0, creature.reproduction_cooldown_remaining - dt)
            if creature.age >= creature.traits.max_age:
                event = self._kill_creature(creature, DeathCause.OLD_AGE)
                if event is not None:
                    events.append(event)
        return events

    def _update_herbivore(self, herbivore: Herbivore, dt: float) -> List[SimulationEvent]:
        assert herbivore.traits is not None
        threat_range = min(herbivore.traits.vision_range, herbivore.traits.flee_distance)
        predators = self.predator_index.query_radius(herbivore.position, threat_range)
        visible_predators = self.perception.visible_entities(herbivore, predators)
        if herbivore.is_hungry():
            plants = self.plant_index.query_radius(herbivore.position, herbivore.traits.vision_range)
            visible_plants = self.perception.visible_entities(herbivore, plants)
        else:
            visible_plants = []
        decision = self.herbivore_policy.decide(herbivore, visible_predators, visible_plants, self.rng)
        herbivore.behavior = decision.state
        herbivore.target_id = decision.target_id

        events: List[SimulationEvent] = []
        if decision.should_reproduce:
            events.extend(self._try_reproduce(herbivore))
        events.extend(self._move_and_charge_energy(herbivore, decision.desired_velocity, dt))
        if herbivore.alive:
            feeding_event = self._consume_nearby_plant(herbivore)
            if feeding_event is not None:
                events.append(feeding_event)
        return events

    def _update_predator(self, predator: Predator, dt: float) -> List[SimulationEvent]:
        assert predator.traits is not None
        close_distance = predator.traits.attack_range + predator.traits.max_speed
        search_radius = predator.traits.vision_range if predator.is_hungry() else close_distance
        prey = self.herbivore_index.query_radius(predator.position, search_radius)
        visible_prey = self.perception.visible_entities(predator, prey)
        decision = self.predator_policy.decide(predator, visible_prey, self.rng)
        predator.behavior = decision.state
        predator.target_id = decision.target_id

        events: List[SimulationEvent] = []
        if decision.should_reproduce:
            events.extend(self._try_reproduce(predator))
        events.extend(self._move_and_charge_energy(predator, decision.desired_velocity, dt))
        if predator.alive:
            events.extend(self._attack_nearby_prey(predator))
        return events

    def _move_and_charge_energy(
        self,
        creature: Creature,
        desired_velocity: np.ndarray,
        dt: float,
    ) -> List[SimulationEvent]:
        if not creature.alive:
            return []
        assert creature.traits is not None
        velocity = self._steer_velocity(creature, desired_velocity, dt)
        old_position = creature.position.copy()
        new_position = old_position + velocity * dt
        new_position, velocity = self._apply_bounds(old_position, new_position, velocity, dt)
        creature.position = new_position
        creature.velocity = velocity
        speed = length(velocity)
        if speed > EPSILON:
            creature.heading = normalize(velocity)
        distance = float(np.linalg.norm(creature.position - old_position))
        creature.apply_energy_cost(distance, dt)
        creature.register_behavior_time(dt)
        if creature.energy <= 0.0:
            event = self._kill_creature(creature, DeathCause.FAMINE)
            return [event] if event is not None else []
        return []

    def _steer_velocity(
        self,
        creature: Creature,
        desired_velocity: np.ndarray,
        dt: float,
    ) -> np.ndarray:
        assert creature.traits is not None
        desired_velocity = clamp_magnitude(desired_velocity, creature.traits.max_speed)
        desired_speed = length(desired_velocity)
        if desired_speed <= EPSILON:
            return np.zeros(2, dtype=float)

        desired_direction = normalize(desired_velocity)
        reference_velocity = creature.velocity if length(creature.velocity) > EPSILON else creature.heading
        current_direction = normalize(reference_velocity)
        if length(current_direction) <= EPSILON:
            return desired_velocity

        max_turn = MAX_CREATURE_TURN_RATE * dt
        dot = float(np.clip(np.dot(current_direction, desired_direction), -1.0, 1.0))
        angle = float(np.arccos(dot))
        if angle <= max_turn:
            return desired_velocity

        cross = float(
            current_direction[0] * desired_direction[1]
            - current_direction[1] * desired_direction[0]
        )
        turn = max_turn if cross >= 0.0 else -max_turn
        cos_turn = float(np.cos(turn))
        sin_turn = float(np.sin(turn))
        steered_direction = np.array(
            [
                current_direction[0] * cos_turn - current_direction[1] * sin_turn,
                current_direction[0] * sin_turn + current_direction[1] * cos_turn,
            ],
            dtype=float,
        )
        return normalize(steered_direction) * desired_speed

    def _apply_bounds(
        self,
        old_position: np.ndarray,
        new_position: np.ndarray,
        velocity: np.ndarray,
        dt: float,
    ) -> Sequence[np.ndarray]:
        width, height = self.config.world_width, self.config.world_height
        bounded = new_position.copy()
        adjusted_velocity = velocity.copy()
        if bounded[0] < 0.0 or bounded[0] > width:
            bounded[0] = float(np.clip(bounded[0], 0.0, width))
            adjusted_velocity[0] *= -0.45
        if bounded[1] < 0.0 or bounded[1] > height:
            bounded[1] = float(np.clip(bounded[1], 0.0, height))
            adjusted_velocity[1] *= -0.45
        if dt > 0.0 and np.any(bounded != new_position):
            adjusted_velocity = (bounded - old_position) / dt
        return bounded, adjusted_velocity

    def _consume_nearby_plant(self, herbivore: Herbivore) -> Optional[SimulationEvent]:
        assert herbivore.traits is not None
        nearby = self.plant_index.query_radius(herbivore.position, herbivore.radius + self.config.plant.radius + 2.0)
        living = [plant for plant in nearby if getattr(plant, "alive", False)]
        if not living:
            return None
        plant = min(living, key=herbivore.distance_to)
        plant.alive = False
        gain = min(getattr(plant, "energy"), herbivore.traits.food_energy_gain)
        herbivore.energy += gain
        herbivore.clamp_energy()
        return SimulationEvent(
            time=self.time,
            kind=EventKind.FEEDING,
            species=herbivore.kind,
            entity_id=herbivore.id,
            target_id=getattr(plant, "id", None),
            energy=gain,
        )

    def _attack_nearby_prey(self, predator: Predator) -> List[SimulationEvent]:
        assert predator.traits is not None
        radius = predator.traits.attack_range + predator.radius + 6.0
        candidates = self.herbivore_index.query_radius(predator.position, radius)
        living = [prey for prey in candidates if getattr(prey, "alive", False)]
        if not living:
            return []
        prey = min(living, key=predator.distance_to)
        if predator.distance_to(prey) > radius:
            return []
        events: List[SimulationEvent] = []
        death = self._kill_creature(prey, DeathCause.PREDATION, predator.id)
        if death is not None:
            events.append(death)
        predator.energy += predator.traits.food_energy_gain
        predator.clamp_energy()
        events.append(
            SimulationEvent(
                time=self.time,
                kind=EventKind.PREDATION,
                species=predator.kind,
                entity_id=predator.id,
                target_id=prey.id,
                energy=predator.traits.food_energy_gain,
            )
        )
        return events

    def _try_reproduce(self, parent: Creature) -> List[SimulationEvent]:
        assert parent.traits is not None
        if not parent.can_reproduce():
            return []
        if self.living_creature_count() >= self.config.max_creatures:
            return []
        parent.energy -= parent.traits.reproduction_cost
        parent.reproduction_cooldown_remaining = parent.traits.reproduction_cooldown
        child_energy = min(parent.traits.max_energy * 0.50, parent.traits.reproduction_cost)
        child_position = jittered_position(
            self.rng,
            parent.position,
            radius=18.0,
            bounds=(self.config.world_width, self.config.world_height),
        )
        child = self.spawn_creature(parent.kind, position=child_position, initial=False, initial_energy=child_energy)
        return [
            SimulationEvent(
                time=self.time,
                kind=EventKind.BIRTH,
                species=parent.kind,
                entity_id=child.id,
                target_id=parent.id,
                energy=child.energy,
            )
        ]

    def _kill_creature(
        self,
        creature: Creature,
        cause: DeathCause,
        predator_id: Optional[int] = None,
    ) -> Optional[SimulationEvent]:
        if not creature.alive:
            return None
        creature.mark_dead(cause)
        return SimulationEvent(
            time=self.time,
            kind=EventKind.DEATH,
            species=creature.kind,
            entity_id=creature.id,
            target_id=predator_id,
            cause=cause,
            energy=creature.energy,
            age=creature.age,
        )

    def _regrow_plants(self, dt: float) -> None:
        living_count = sum(1 for plant in self.plants if plant.alive)
        capacity = self.config.plant.max_count - living_count
        if capacity <= 0:
            self._plant_regrowth_credit = 0.0
            return
        self._plant_regrowth_credit += self.config.plant.regrowth_per_second * dt
        spawn_count = min(int(self._plant_regrowth_credit), capacity)
        if spawn_count <= 0:
            return
        self._plant_regrowth_credit -= spawn_count
        for _ in range(spawn_count):
            self.spawn_plant()

    def _refresh_indices(
        self,
        plants: bool = True,
        herbivores: bool = True,
        predators: bool = True,
    ) -> None:
        if plants:
            self.plant_index.rebuild(self.plants)
        if herbivores:
            self.herbivore_index.rebuild(self.herbivores)
        if predators:
            self.predator_index.rebuild(self.predators)

    def _remove_dead(self) -> None:
        self.plants = [plant for plant in self.plants if plant.alive]
        self.herbivores = [herbivore for herbivore in self.herbivores if herbivore.alive]
        self.predators = [predator for predator in self.predators if predator.alive]
