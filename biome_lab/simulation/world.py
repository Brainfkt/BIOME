from __future__ import annotations

import math
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

import numpy as np
from pydantic import ValidationError

from biome_lab.behavior.herbivore_policy import HerbivorePolicy
from biome_lab.behavior.perception import PerceptionSystem
from biome_lab.behavior.predator_policy import PredatorPolicy
from biome_lab.behavior.steering import (
    EPSILON,
    EPSILON_SQ,
    clamp_magnitude,
    distance_squared,
    length_squared,
    normalize_with_length,
)
from biome_lab.config.schemas import (
    BiomeLabPreset,
    CreatureState,
    CreatureTraits,
    DiseaseState,
    MutableTrait,
    ObstacleConfig,
    PlantState,
    WorldState,
    WorldSystemsState,
    WorldTopologyState,
)
from biome_lab.entities.creatures import BehaviorState, Creature
from biome_lab.entities.herbivores import Herbivore
from biome_lab.entities.plants import Plant
from biome_lab.entities.predators import Predator
from biome_lab.simulation.events import DeathCause, EventKind, SimulationEvent
from biome_lab.simulation.rng import create_rng, jittered_position, random_position, random_unit_vector
from biome_lab.simulation.spatial_index import SpatialIndex


MAX_CREATURE_TURN_RATE = float(np.deg2rad(220.0))
SPATIAL_INDEX_CELL_SIZE = 64.0
MutationChange = Tuple[MutableTrait, float, float]


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
        self.obstacles = list(self.config.environment.obstacles)
        self.zones = list(self.config.environment.zones)
        self.topology_grid = self._build_topology_grid()
        self.events: List[SimulationEvent] = []
        self.last_spawn_error: Optional[str] = None
        self.perception = PerceptionSystem()
        self.herbivore_policy = HerbivorePolicy()
        self.predator_policy = PredatorPolicy()
        self.plant_index = SpatialIndex(cell_size=SPATIAL_INDEX_CELL_SIZE)
        self.herbivore_index = SpatialIndex(cell_size=SPATIAL_INDEX_CELL_SIZE)
        self.predator_index = SpatialIndex(cell_size=SPATIAL_INDEX_CELL_SIZE)
        self._nearby_predators_buffer: List[object] = []
        self._visible_predators_buffer: List[object] = []
        self._nearby_plants_buffer: List[object] = []
        self._visible_plants_buffer: List[object] = []
        self._nearby_prey_buffer: List[object] = []
        self._visible_prey_buffer: List[object] = []
        self._nearby_creatures_buffer: List[Creature] = []
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
        self.obstacles = list(self.config.environment.obstacles)
        self.zones = list(self.config.environment.zones)
        self.topology_grid = self._build_topology_grid()
        self.events = []
        self.last_spawn_error = None
        self._clear_query_buffers()
        for _ in range(self.config.plant.initial_count):
            self.spawn_plant()
        for _ in range(self.config.initial_herbivores):
            self.spawn_creature("herbivore", initial=True)
        for _ in range(self.config.initial_predators):
            self.spawn_creature("predator", initial=True)
        self.events.extend(self._seed_initial_infections())
        self._refresh_indices()

    def _clear_query_buffers(self) -> None:
        self._nearby_predators_buffer.clear()
        self._visible_predators_buffer.clear()
        self._nearby_plants_buffer.clear()
        self._visible_plants_buffer.clear()
        self._nearby_prey_buffer.clear()
        self._visible_prey_buffer.clear()
        self._nearby_creatures_buffer.clear()

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

    def current_season_index(self) -> int:
        seasons = self.config.seasons
        if not seasons.enabled or not seasons.phases:
            return -1
        total_fraction = sum(phase.duration_fraction for phase in seasons.phases)
        cycle_position = (self.time % seasons.cycle_seconds) / seasons.cycle_seconds * total_fraction
        cursor = 0.0
        for index, phase in enumerate(seasons.phases):
            cursor += phase.duration_fraction
            if cycle_position <= cursor:
                return index
        return len(seasons.phases) - 1

    def current_season_name(self) -> str:
        index = self.current_season_index()
        if index < 0:
            return "none"
        return self.config.seasons.phases[index].name

    def topology_enabled(self) -> bool:
        return self.config.topology.enabled

    def sample_elevation(self, position: np.ndarray) -> float:
        rows, columns = self.topology_grid.shape
        x = float(np.clip(position[0], 0.0, self.config.world_width))
        y = float(np.clip(position[1], 0.0, self.config.world_height))
        grid_x = x / max(float(self.config.world_width), 1.0) * (columns - 1)
        grid_y = y / max(float(self.config.world_height), 1.0) * (rows - 1)
        x0 = int(np.floor(grid_x))
        y0 = int(np.floor(grid_y))
        x1 = min(x0 + 1, columns - 1)
        y1 = min(y0 + 1, rows - 1)
        tx = grid_x - x0
        ty = grid_y - y0
        top = (1.0 - tx) * self.topology_grid[y0, x0] + tx * self.topology_grid[y0, x1]
        bottom = (1.0 - tx) * self.topology_grid[y1, x0] + tx * self.topology_grid[y1, x1]
        return float((1.0 - ty) * top + ty * bottom)

    def topology_summary(self) -> Dict[str, float]:
        return {
            "enabled": float(self.config.topology.enabled),
            "min_elevation": float(np.min(self.topology_grid)),
            "max_elevation": float(np.max(self.topology_grid)),
            "mean_elevation": float(np.mean(self.topology_grid)),
            "roughness": float(np.std(self.topology_grid)),
        }

    def apply_topology_brush(
        self,
        center: np.ndarray,
        radius: float,
        strength: float,
        mode: str,
    ) -> None:
        self.config.topology.enabled = True
        rows, columns = self.topology_grid.shape
        xs = np.linspace(0.0, self.config.world_width, columns)
        ys = np.linspace(0.0, self.config.world_height, rows)
        grid_x, grid_y = np.meshgrid(xs, ys)
        distance_sq = (grid_x - center[0]) ** 2 + (grid_y - center[1]) ** 2
        radius = max(float(radius), 1.0)
        mask = distance_sq <= radius * radius
        if not np.any(mask):
            return
        weight = np.exp(-distance_sq / max(2.0 * (radius * 0.45) ** 2, 1.0))
        weight *= mask
        effective_strength = max(0.0, min(float(strength), 1.0))
        if mode == "valley":
            self.topology_grid -= weight * effective_strength
        elif mode == "ridge":
            self.topology_grid += weight * effective_strength
        elif mode == "smooth":
            local_mean = float(np.mean(self.topology_grid[mask]))
            self.topology_grid[mask] = (
                self.topology_grid[mask] * (1.0 - weight[mask] * effective_strength)
                + local_mean * weight[mask] * effective_strength
            )
        else:
            raise ValueError("unknown topology brush mode: %s" % mode)
        self.topology_grid = np.clip(self.topology_grid, 0.0, 1.0)

    def find_creature(self, entity_id: int) -> Optional[Creature]:
        for creature in self.iter_creatures():
            if creature.id == entity_id:
                return creature
        return None

    def refresh_indices(self) -> None:
        self._refresh_indices()

    @classmethod
    def from_world_state(cls, state: WorldState) -> "World":
        if not isinstance(state, WorldState):
            state = WorldState.model_validate(state)
        world = cls(state.preset)
        world.time = state.time
        world._plant_regrowth_credit = state.plant_regrowth_credit
        world.obstacles = list(state.obstacles)
        world.zones = list(state.zones)
        world.config.environment.obstacles = list(state.obstacles)
        world.config.environment.zones = list(state.zones)
        world.config.topology.enabled = state.systems.topology
        world.config.seasons.enabled = state.systems.seasons
        world.config.disease.enabled = state.systems.disease
        world.config.mutation.enabled = state.systems.mutation
        world.config.topology.palette = state.topology.palette
        world.topology_grid = np.array(state.topology.grid, dtype=float)
        world.plants = [
            Plant(
                id=plant.id,
                position=np.array(plant.position, dtype=float),
                radius=plant.radius,
                kind="plant",
                energy=plant.energy,
                alive=plant.alive,
            )
            for plant in state.plants
        ]
        world.herbivores = []
        world.predators = []
        for creature_state in state.creatures:
            creature = world._creature_from_state(creature_state)
            if creature.kind == "herbivore":
                world.herbivores.append(creature)
            else:
                world.predators.append(creature)
        max_loaded_id = max(
            [0]
            + [plant.id for plant in world.plants]
            + [creature.id for creature in world.iter_creatures()]
        )
        world._id_counter = max(state.id_counter, max_loaded_id)
        world.rng = create_rng(world.config.seed)
        world.rng.bit_generator.state = state.rng_state
        world.events = []
        world.last_spawn_error = None
        world._refresh_indices()
        return world

    def to_world_state(self) -> WorldState:
        preset = self.preset.model_copy(deep=True)
        preset.simulation.environment.obstacles = list(self.obstacles)
        preset.simulation.environment.zones = list(self.zones)
        preset.simulation.topology.enabled = self.config.topology.enabled
        preset.simulation.topology.palette = self.config.topology.palette
        preset.simulation.seasons.enabled = self.config.seasons.enabled
        preset.simulation.disease.enabled = self.config.disease.enabled
        preset.simulation.mutation.enabled = self.config.mutation.enabled
        return WorldState(
            preset=preset,
            time=self.time,
            id_counter=self._id_counter,
            plant_regrowth_credit=self._plant_regrowth_credit,
            rng_state=self.rng.bit_generator.state,
            systems=WorldSystemsState(
                topology=self.config.topology.enabled,
                seasons=self.config.seasons.enabled,
                disease=self.config.disease.enabled,
                mutation=self.config.mutation.enabled,
            ),
            plants=[
                PlantState(
                    id=plant.id,
                    position=(float(plant.position[0]), float(plant.position[1])),
                    radius=plant.radius,
                    energy=plant.energy,
                    alive=plant.alive,
                )
                for plant in self.plants
            ],
            creatures=[
                CreatureState(
                    id=creature.id,
                    species=creature.kind,
                    position=(float(creature.position[0]), float(creature.position[1])),
                    radius=creature.radius,
                    traits=creature.traits,
                    velocity=(float(creature.velocity[0]), float(creature.velocity[1])),
                    heading=(float(creature.heading[0]), float(creature.heading[1])),
                    energy=creature.energy,
                    age=creature.age,
                    birth_time=creature.birth_time,
                    reproduction_cooldown_remaining=creature.reproduction_cooldown_remaining,
                    behavior=creature.behavior.value,
                    target_id=creature.target_id,
                    disease_state=creature.disease_state,
                    infection_timer=creature.infection_timer,
                    generation=creature.generation,
                    mutation_count=creature.mutation_count,
                    alive=creature.alive,
                )
                for creature in self.iter_creatures()
            ],
            obstacles=list(self.obstacles),
            zones=list(self.zones),
            topology=WorldTopologyState(
                enabled=self.config.topology.enabled,
                palette=self.config.topology.palette,
                grid=self.topology_grid.tolist(),
            ),
        )

    def _creature_from_state(self, state: CreatureState) -> Creature:
        kwargs = {
            "id": state.id,
            "position": np.array(state.position, dtype=float),
            "radius": state.radius,
            "kind": state.species,
            "traits": state.traits,
            "velocity": np.array(state.velocity, dtype=float),
            "heading": np.array(state.heading, dtype=float),
            "energy": state.energy,
            "age": state.age,
            "birth_time": state.birth_time,
            "reproduction_cooldown_remaining": state.reproduction_cooldown_remaining,
            "behavior": BehaviorState(state.behavior),
            "target_id": state.target_id,
            "disease_state": state.disease_state,
            "infection_timer": state.infection_timer,
            "generation": state.generation,
            "mutation_count": state.mutation_count,
            "alive": state.alive,
        }
        if state.species == "herbivore":
            return Herbivore(**kwargs)
        return Predator(**kwargs)

    def set_system_enabled(
        self,
        system: str,
        enabled: bool,
        preferred_id: Optional[int] = None,
    ) -> List[SimulationEvent]:
        events = [
            SimulationEvent(
                time=self.time,
                kind=EventKind.SYSTEM_TOGGLE,
                species="system",
                entity_id=0,
                system=system,
                enabled=enabled,
            )
        ]
        if system == "topology":
            self.config.topology.enabled = enabled
        elif system == "seasons":
            self.config.seasons.enabled = enabled
        elif system == "disease":
            self.config.disease.enabled = enabled
            if enabled:
                events.extend(
                    self.seed_infections(
                        max(1, self.config.disease.initial_infected),
                        preferred_id=preferred_id,
                    )
                )
        elif system == "mutation":
            self.config.mutation.enabled = enabled
        else:
            raise ValueError("unknown configurable system: %s" % system)
        self.events.extend(events)
        return events

    def seed_infections(
        self,
        count: int = 1,
        preferred_id: Optional[int] = None,
    ) -> List[SimulationEvent]:
        if count <= 0:
            return []
        susceptible = [
            creature
            for creature in self.iter_living_creatures()
            if creature.disease_state == DiseaseState.SUSCEPTIBLE
        ]
        if not susceptible:
            return []
        events: List[SimulationEvent] = []
        if preferred_id is not None:
            preferred = next((creature for creature in susceptible if creature.id == preferred_id), None)
            if preferred is not None:
                preferred.infect()
                susceptible.remove(preferred)
                events.append(
                    SimulationEvent(
                        time=self.time,
                        kind=EventKind.INITIAL_INFECTION,
                        species=preferred.kind,
                        entity_id=preferred.id,
                    )
                )
        remaining = max(0, count - len(events))
        if remaining > 0 and susceptible:
            take = min(remaining, len(susceptible))
            indices = self.rng.choice(len(susceptible), size=take, replace=False)
            for index in np.atleast_1d(indices):
                creature = susceptible[int(index)]
                creature.infect()
                events.append(
                    SimulationEvent(
                        time=self.time,
                        kind=EventKind.INITIAL_INFECTION,
                        species=creature.kind,
                        entity_id=creature.id,
                    )
                )
        return events

    def add_obstacle_rect(
        self,
        center: np.ndarray,
        width: float = 80.0,
        height: float = 50.0,
        name: str = "sandbox_obstacle",
    ) -> ObstacleConfig:
        obstacle = ObstacleConfig(
            name=name,
            x=float(np.clip(center[0] - width / 2.0, 0.0, max(0.0, self.config.world_width - width))),
            y=float(np.clip(center[1] - height / 2.0, 0.0, max(0.0, self.config.world_height - height))),
            width=width,
            height=height,
            blocks_movement=True,
        )
        self.obstacles.append(obstacle)
        self.config.environment.obstacles.append(obstacle)
        return obstacle

    def remove_entity_at(self, position: np.ndarray, radius: float = 18.0) -> bool:
        candidates = [
            entity
            for entity in list(self.iter_creatures()) + list(self.plants)
            if getattr(entity, "alive", False)
        ]
        if candidates:
            nearest = min(candidates, key=lambda entity: entity.distance_to_position(position))
            if nearest.distance_to_position(position) <= radius:
                nearest.alive = False
                self._remove_dead()
                self._refresh_indices()
                return True
        for obstacle in list(self.obstacles):
            if self._point_in_rect(position, obstacle):
                self.obstacles.remove(obstacle)
                if obstacle in self.config.environment.obstacles:
                    self.config.environment.obstacles.remove(obstacle)
                return True
        return False

    def to_state_dict(self) -> Dict[str, object]:
        return {
            "time": self.time,
            "season": self.current_season_name(),
            "plants": [
                {
                    "id": plant.id,
                    "x": float(plant.position[0]),
                    "y": float(plant.position[1]),
                    "energy": plant.energy,
                }
                for plant in self.plants
                if plant.alive
            ],
            "creatures": [
                {
                    "id": creature.id,
                    "species": creature.kind,
                    "x": float(creature.position[0]),
                    "y": float(creature.position[1]),
                    "energy": creature.energy,
                    "age": creature.age,
                    "disease_state": creature.disease_state.value,
                    "generation": creature.generation,
                    "mutation_count": creature.mutation_count,
                }
                for creature in self.iter_living_creatures()
            ],
            "obstacles": [obstacle.model_dump() for obstacle in self.obstacles],
            "zones": [zone.model_dump() for zone in self.zones],
            "topology": {
                "palette": self.config.topology.palette,
                "summary": self.topology_summary(),
                "grid": np.round(self.topology_grid, 4).tolist(),
            },
        }

    def spawn_plant(self, position: Optional[np.ndarray] = None) -> Optional[Plant]:
        if position is None:
            position = self._random_free_position(self.config.plant.radius)
        if position is None:
            self.last_spawn_error = "no free position available for plant"
            return None
        if not self._position_in_bounds(position, self.config.plant.radius):
            self.last_spawn_error = "plant spawn position is outside world bounds"
            return None
        if self._position_blocked(position, self.config.plant.radius):
            self.last_spawn_error = "plant spawn position is blocked by an obstacle"
            return None
        plant = Plant(
            id=self.next_id(),
            position=position,
            radius=self.config.plant.radius,
            kind="plant",
            energy=self.config.plant.energy,
        )
        self.plants.append(plant)
        self.last_spawn_error = None
        return plant

    def spawn_creature(
        self,
        species: str,
        position: Optional[np.ndarray] = None,
        initial: bool = False,
        initial_energy: Optional[float] = None,
        traits_override: Optional[CreatureTraits] = None,
        generation: int = 0,
        mutation_count: int = 0,
    ) -> Optional[Creature]:
        if self.living_creature_count() >= self.config.max_creatures:
            self.last_spawn_error = "max_creatures limit reached"
            return None
        if species == "herbivore":
            traits = traits_override or self.preset.herbivore
            radius = self.config.herbivore_radius
        elif species == "predator":
            traits = traits_override or self.preset.predator
            radius = self.config.predator_radius
        else:
            raise ValueError("unknown creature species: %s" % species)
        if position is None:
            position = self._random_free_position(radius)
        if position is None:
            self.last_spawn_error = "no free position available for %s" % species
            return None
        if not self._position_in_bounds(position, radius):
            self.last_spawn_error = "%s spawn position is outside world bounds" % species
            return None
        if self._position_blocked(position, radius):
            self.last_spawn_error = "%s spawn position is blocked by an obstacle" % species
            return None
        if initial_energy is None:
            low_fraction = self.config.initial_energy_min_fraction if initial else self.config.birth_energy_min_fraction
            high_fraction = self.config.initial_energy_max_fraction if initial else self.config.birth_energy_max_fraction
            low = traits.max_energy * low_fraction
            high = traits.max_energy * high_fraction
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
            "generation": generation,
            "mutation_count": mutation_count,
        }
        if species == "herbivore":
            creature: Creature = Herbivore(**kwargs)
            self.herbivores.append(creature)
        else:
            creature = Predator(**kwargs)
            self.predators.append(creature)
        self.last_spawn_error = None
        return creature

    def update(self, dt: float) -> List[SimulationEvent]:
        dt = max(0.0, min(float(dt), 0.25))
        if dt <= 0.0:
            return []
        self.time += dt
        events: List[SimulationEvent] = []
        events.extend(self._age_and_check_mortality(dt))
        if self.config.disease.enabled:
            self._refresh_indices()
        else:
            self._refresh_indices(herbivores=False)
        events.extend(self._update_disease(dt))

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

    def _seed_initial_infections(self) -> List[SimulationEvent]:
        disease = self.config.disease
        if not disease.enabled or disease.initial_infected <= 0:
            return []
        return self.seed_infections(disease.initial_infected)

    def _update_disease(self, dt: float) -> List[SimulationEvent]:
        disease = self.config.disease
        if not disease.enabled:
            return []

        events: List[SimulationEvent] = []
        infected = [
            creature
            for creature in self.iter_living_creatures()
            if creature.disease_state == DiseaseState.INFECTED
        ]
        if not infected:
            return []

        for source in infected:
            source.infection_timer += dt
            source.energy -= disease.energy_drain_per_second * dt
            if source.energy <= 0.0:
                death = self._kill_creature(source, DeathCause.DISEASE)
                if death is not None:
                    events.append(death)
                continue

            mortality_risk = 1.0 - math.exp(-disease.mortality_probability_per_second * dt)
            if mortality_risk > 0.0 and float(self.rng.random()) < mortality_risk:
                death = self._kill_creature(source, DeathCause.DISEASE)
                if death is not None:
                    events.append(death)
                continue

            if source.infection_timer >= disease.recovery_seconds:
                source.recover()
                events.append(
                    SimulationEvent(
                        time=self.time,
                        kind=EventKind.RECOVERY,
                        species=source.kind,
                        entity_id=source.id,
                    )
                )
                continue

            candidates = self._nearby_creatures(source.position, disease.transmission_radius)
            for target in candidates:
                if target.id == source.id or not target.alive:
                    continue
                if target.disease_state != DiseaseState.SUSCEPTIBLE:
                    continue
                risk = disease.transmission_probability_per_second
                risk *= self._disease_multiplier_at(target.position)
                risk = min(1.0, risk * dt)
                if risk > 0.0 and float(self.rng.random()) < risk:
                    target.infect()
                    events.append(
                        SimulationEvent(
                            time=self.time,
                            kind=EventKind.INFECTION,
                            species=target.kind,
                            entity_id=target.id,
                            target_id=source.id,
                        )
                    )
        return events

    def _update_herbivore(self, herbivore: Herbivore, dt: float) -> List[SimulationEvent]:
        assert herbivore.traits is not None
        threat_range = min(herbivore.traits.vision_range, herbivore.traits.flee_distance)
        predators = self.predator_index.query_radius_into(
            herbivore.position,
            threat_range,
            self._nearby_predators_buffer,
        )
        visible_predators = self.perception.visible_entities_into(
            herbivore,
            predators,
            self._visible_predators_buffer,
            assume_in_range=True,
        )
        if herbivore.is_hungry():
            plants = self.plant_index.query_radius_into(
                herbivore.position,
                herbivore.traits.vision_range,
                self._nearby_plants_buffer,
            )
            visible_plants = self.perception.visible_entities_into(
                herbivore,
                plants,
                self._visible_plants_buffer,
                assume_in_range=True,
            )
        else:
            visible_plants = self._visible_plants_buffer
            visible_plants.clear()
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
        prey = self.herbivore_index.query_radius_into(
            predator.position,
            search_radius,
            self._nearby_prey_buffer,
        )
        visible_prey = self.perception.visible_entities_into(
            predator,
            prey,
            self._visible_prey_buffer,
            assume_in_range=search_radius <= predator.traits.vision_range,
        )
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
        old_position = creature.position
        old_x = float(old_position[0])
        old_y = float(old_position[1])
        new_position = np.array(
            [
                old_x + float(velocity[0]) * dt,
                old_y + float(velocity[1]) * dt,
            ],
            dtype=float,
        )
        new_position, velocity = self._apply_bounds(old_position, new_position, velocity, dt)
        new_position, velocity = self._apply_obstacles(old_position, new_position, velocity, creature.radius)
        creature.position = new_position
        creature.velocity = velocity
        velocity_direction, speed = normalize_with_length(velocity)
        if speed > EPSILON:
            creature.heading = velocity_direction
        movement_x = float(creature.position[0]) - old_x
        movement_y = float(creature.position[1]) - old_y
        distance = math.sqrt(movement_x * movement_x + movement_y * movement_y)
        metabolism_multiplier = self._metabolism_multiplier_at(creature.position)
        movement_cost_multiplier = self._movement_cost_multiplier_at(creature.position)
        creature.energy -= creature.traits.basal_metabolism * metabolism_multiplier * dt
        creature.energy -= creature.traits.movement_energy_cost * movement_cost_multiplier * distance
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
        max_speed = creature.traits.max_speed * self._speed_multiplier_at(creature.position)
        desired_velocity = clamp_magnitude(desired_velocity, max_speed)
        desired_direction, desired_speed = normalize_with_length(desired_velocity)
        if desired_speed <= EPSILON:
            return np.zeros(2, dtype=float)

        reference_velocity = (
            creature.velocity
            if length_squared(creature.velocity) > EPSILON_SQ
            else creature.heading
        )
        current_direction, current_speed = normalize_with_length(reference_velocity)
        if current_speed <= EPSILON:
            return desired_velocity

        max_turn = math.radians(self.config.creature_turn_rate_deg) * dt
        current_x = float(current_direction[0])
        current_y = float(current_direction[1])
        desired_x = float(desired_direction[0])
        desired_y = float(desired_direction[1])
        dot = current_x * desired_x + current_y * desired_y
        if dot < -1.0:
            dot = -1.0
        elif dot > 1.0:
            dot = 1.0
        angle = math.acos(dot)
        if angle <= max_turn:
            return desired_velocity

        cross = current_x * desired_y - current_y * desired_x
        turn = max_turn if cross >= 0.0 else -max_turn
        cos_turn = math.cos(turn)
        sin_turn = math.sin(turn)
        return np.array(
            [
                (current_x * cos_turn - current_y * sin_turn) * desired_speed,
                (current_x * sin_turn + current_y * cos_turn) * desired_speed,
            ],
            dtype=float,
        )

    def _apply_bounds(
        self,
        old_position: np.ndarray,
        new_position: np.ndarray,
        velocity: np.ndarray,
        dt: float,
    ) -> Sequence[np.ndarray]:
        width, height = self.config.world_width, self.config.world_height
        bounded = new_position
        adjusted_velocity = velocity
        if bounded[0] < 0.0:
            bounded[0] = 0.0
            adjusted_velocity[0] *= -self.config.boundary_bounce
        elif bounded[0] > width:
            bounded[0] = width
            adjusted_velocity[0] *= -self.config.boundary_bounce
        if bounded[1] < 0.0:
            bounded[1] = 0.0
            adjusted_velocity[1] *= -self.config.boundary_bounce
        elif bounded[1] > height:
            bounded[1] = height
            adjusted_velocity[1] *= -self.config.boundary_bounce
        return bounded, adjusted_velocity

    def _apply_obstacles(
        self,
        old_position: np.ndarray,
        new_position: np.ndarray,
        velocity: np.ndarray,
        radius: float,
    ) -> Sequence[np.ndarray]:
        if self._position_blocked(new_position, radius):
            return old_position, np.zeros(2, dtype=float)
        return new_position, velocity

    def _random_free_position(self, radius: float) -> Optional[np.ndarray]:
        for _ in range(100):
            position = random_position(
                self.rng,
                self.config.world_width,
                self.config.world_height,
                padding=radius,
            )
            if self._position_in_bounds(position, radius) and not self._position_blocked(position, radius):
                return position
        return None

    def _position_in_bounds(self, position: np.ndarray, radius: float) -> bool:
        return (
            radius <= float(position[0]) <= self.config.world_width - radius
            and radius <= float(position[1]) <= self.config.world_height - radius
        )

    def _position_blocked(self, position: np.ndarray, radius: float) -> bool:
        for obstacle in self.obstacles:
            if obstacle.blocks_movement and self._circle_intersects_rect(position, radius, obstacle):
                return True
        return False

    def _point_in_rect(self, position: np.ndarray, rect) -> bool:
        return (
            rect.x <= float(position[0]) <= rect.x + rect.width
            and rect.y <= float(position[1]) <= rect.y + rect.height
        )

    def _circle_intersects_rect(self, position: np.ndarray, radius: float, rect) -> bool:
        nearest_x = float(np.clip(position[0], rect.x, rect.x + rect.width))
        nearest_y = float(np.clip(position[1], rect.y, rect.y + rect.height))
        delta_x = float(position[0]) - nearest_x
        delta_y = float(position[1]) - nearest_y
        return delta_x * delta_x + delta_y * delta_y <= radius * radius

    def _zone_at(self, position: np.ndarray):
        for zone in self.zones:
            if self._point_in_rect(position, zone):
                return zone
        return None

    def _season_phase(self):
        index = self.current_season_index()
        if index < 0:
            return None
        return self.config.seasons.phases[index]

    def _speed_multiplier_at(self, position: np.ndarray) -> float:
        zone = self._zone_at(position)
        return 1.0 if zone is None else zone.speed_multiplier

    def _metabolism_multiplier_at(self, position: np.ndarray) -> float:
        multiplier = 1.0
        zone = self._zone_at(position)
        season = self._season_phase()
        if zone is not None:
            multiplier *= zone.metabolism_multiplier
        if season is not None:
            multiplier *= season.metabolism_multiplier
        return multiplier

    def _movement_cost_multiplier_at(self, position: np.ndarray) -> float:
        multiplier = 1.0
        zone = self._zone_at(position)
        season = self._season_phase()
        if zone is not None:
            multiplier *= zone.movement_cost_multiplier
        if season is not None:
            multiplier *= season.movement_cost_multiplier
        multiplier *= self._topology_movement_cost_multiplier_at(position)
        return multiplier

    def _build_topology_grid(self) -> np.ndarray:
        topology = self.config.topology
        grid = np.full(
            (topology.grid_rows, topology.grid_columns),
            topology.base_elevation,
            dtype=float,
        )
        if not topology.features:
            return np.clip(grid, 0.0, 1.0)

        xs = np.linspace(0.0, self.config.world_width, topology.grid_columns)
        ys = np.linspace(0.0, self.config.world_height, topology.grid_rows)
        grid_x, grid_y = np.meshgrid(xs, ys)
        for feature in topology.features:
            angle = float(np.deg2rad(feature.orientation_deg))
            cos_angle = float(np.cos(angle))
            sin_angle = float(np.sin(angle))
            dx = grid_x - feature.x
            dy = grid_y - feature.y
            along = dx * cos_angle + dy * sin_angle
            across = -dx * sin_angle + dy * cos_angle
            length_scale = max(feature.length / 2.0, 1.0)
            width_scale = max(feature.width / 2.0, 1.0)
            influence = np.exp(
                -(
                    (along ** 2) / (2.0 * length_scale ** 2)
                    + (across ** 2) / (2.0 * width_scale ** 2)
                )
            )
            if feature.kind in ("valley", "basin"):
                grid -= influence * feature.strength
            elif feature.kind in ("ridge", "hill"):
                grid += influence * feature.strength
        return np.clip(grid, 0.0, 1.0)

    def _topology_slope_at(self, position: np.ndarray) -> float:
        if not self.config.topology.enabled:
            return 0.0
        rows, columns = self.topology_grid.shape
        x_index = int(np.clip(position[0] / max(float(self.config.world_width), 1.0) * (columns - 1), 0, columns - 1))
        y_index = int(np.clip(position[1] / max(float(self.config.world_height), 1.0) * (rows - 1), 0, rows - 1))
        left = self.topology_grid[y_index, max(0, x_index - 1)]
        right = self.topology_grid[y_index, min(columns - 1, x_index + 1)]
        up = self.topology_grid[max(0, y_index - 1), x_index]
        down = self.topology_grid[min(rows - 1, y_index + 1), x_index]
        return float(np.sqrt((right - left) ** 2 + (down - up) ** 2))

    def _topology_movement_cost_multiplier_at(self, position: np.ndarray) -> float:
        if not self.config.topology.enabled:
            return 1.0
        return 1.0 + self._topology_slope_at(position) * self.config.topology.movement_cost_per_slope

    def _plant_regrowth_multiplier(self) -> float:
        season = self._season_phase()
        return 1.0 if season is None else season.plant_regrowth_multiplier

    def _disease_multiplier_at(self, position: np.ndarray) -> float:
        multiplier = 1.0
        zone = self._zone_at(position)
        season = self._season_phase()
        if zone is not None:
            multiplier *= zone.disease_transmission_multiplier
        if season is not None:
            multiplier *= season.disease_transmission_multiplier
        return multiplier

    def _nearby_creatures(self, position: np.ndarray, radius: float) -> List[Creature]:
        creatures = self._nearby_creatures_buffer
        creatures.clear()
        self.herbivore_index.query_radius_into(position, radius, creatures)
        self.predator_index.query_radius_into(position, radius, creatures, clear=False)
        return creatures

    def _child_traits(self, parent: Creature) -> Tuple[CreatureTraits, Optional[MutationChange]]:
        assert parent.traits is not None
        mutation = self.config.mutation
        if not mutation.enabled or float(self.rng.random()) >= mutation.probability:
            return parent.traits, None

        base_traits = self.preset.herbivore if parent.kind == "herbivore" else self.preset.predator
        candidates: List[MutableTrait] = []
        for trait_name in mutation.mutable_traits:
            if not hasattr(parent.traits, trait_name) or not hasattr(base_traits, trait_name):
                continue
            current_value = getattr(parent.traits, trait_name)
            base_value = getattr(base_traits, trait_name)
            if not isinstance(current_value, (int, float)) or not isinstance(base_value, (int, float)):
                continue
            bounds = mutation.trait_bounds.get(trait_name)
            if bounds is None:
                continue
            lower = max(bounds.min_value, float(base_value) * mutation.min_trait_multiplier)
            upper = min(bounds.max_value, float(base_value) * mutation.max_trait_multiplier)
            if upper <= lower:
                continue
            candidates.append(trait_name)
        if not candidates:
            return parent.traits, None

        for index in np.atleast_1d(self.rng.permutation(len(candidates))):
            trait_name = candidates[int(index)]
            current_value = float(getattr(parent.traits, trait_name))
            base_value = float(getattr(base_traits, trait_name))
            bounds = mutation.trait_bounds[trait_name]
            factor = 1.0 + float(self.rng.uniform(-mutation.strength, mutation.strength))
            lower = max(bounds.min_value, base_value * mutation.min_trait_multiplier)
            upper = min(bounds.max_value, base_value * mutation.max_trait_multiplier)
            new_value = float(np.clip(current_value * factor, lower, upper))
            if abs(new_value - current_value) <= 1e-12:
                continue
            data = parent.traits.model_dump()
            data[trait_name] = new_value
            try:
                return CreatureTraits.model_validate(data), (trait_name, current_value, new_value)
            except ValidationError:
                continue
        return parent.traits, None

    def _consume_nearby_plant(self, herbivore: Herbivore) -> Optional[SimulationEvent]:
        assert herbivore.traits is not None
        nearby = self.plant_index.query_radius_into(
            herbivore.position,
            herbivore.radius + self.config.plant.radius + self.config.plant_interaction_margin,
            self._nearby_plants_buffer,
        )
        plant = None
        best_distance_sq = math.inf
        for candidate in nearby:
            if not getattr(candidate, "alive", False):
                continue
            candidate_distance_sq = distance_squared(herbivore.position, getattr(candidate, "position"))
            if candidate_distance_sq < best_distance_sq:
                plant = candidate
                best_distance_sq = candidate_distance_sq
        if plant is None:
            return None
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
        radius = predator.traits.attack_range + predator.radius + self.config.predator_attack_margin
        candidates = self.herbivore_index.query_radius_into(
            predator.position,
            radius,
            self._nearby_prey_buffer,
        )
        prey = None
        best_distance_sq = math.inf
        for candidate in candidates:
            if not getattr(candidate, "alive", False):
                continue
            candidate_distance_sq = distance_squared(predator.position, getattr(candidate, "position"))
            if candidate_distance_sq < best_distance_sq:
                prey = candidate
                best_distance_sq = candidate_distance_sq
        if prey is None:
            return []
        if best_distance_sq > radius * radius:
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
        child_energy = min(parent.traits.max_energy * 0.50, parent.traits.reproduction_cost)
        child_position = jittered_position(
            self.rng,
            parent.position,
            radius=self.config.reproduction_spawn_radius,
            bounds=(self.config.world_width, self.config.world_height),
        )
        if not self._position_in_bounds(child_position, parent.radius) or self._position_blocked(child_position, parent.radius):
            child_position = self._random_free_position(parent.radius)
        if child_position is None:
            self.last_spawn_error = "no free position available for child"
            return []
        child_traits, mutation_change = self._child_traits(parent)
        child = self.spawn_creature(
            parent.kind,
            position=child_position,
            initial=False,
            initial_energy=child_energy,
            traits_override=child_traits,
            generation=parent.generation + 1,
            mutation_count=parent.mutation_count + (1 if mutation_change is not None else 0),
        )
        if child is None:
            return []
        parent.energy -= parent.traits.reproduction_cost
        parent.reproduction_cooldown_remaining = parent.traits.reproduction_cooldown
        events = [
            SimulationEvent(
                time=self.time,
                kind=EventKind.BIRTH,
                species=parent.kind,
                entity_id=child.id,
                target_id=parent.id,
                energy=child.energy,
                generation=child.generation,
                mutation_count=child.mutation_count,
            )
        ]
        if mutation_change is not None:
            trait_name, old_value, new_value = mutation_change
            events.append(
                SimulationEvent(
                    time=self.time,
                    kind=EventKind.MUTATION,
                    species=parent.kind,
                    entity_id=child.id,
                    target_id=parent.id,
                    generation=child.generation,
                    mutation_count=child.mutation_count,
                    mutation_trait=trait_name,
                    old_value=old_value,
                    new_value=new_value,
                )
            )
        return events

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
        self._plant_regrowth_credit += (
            self.config.plant.regrowth_per_second
            * self._plant_regrowth_multiplier()
            * dt
        )
        spawn_count = min(int(self._plant_regrowth_credit), capacity)
        if spawn_count <= 0:
            return
        spawned = 0
        for _ in range(spawn_count):
            if self.spawn_plant() is None:
                break
            spawned += 1
        self._plant_regrowth_credit -= spawned

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
