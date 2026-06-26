from __future__ import annotations

from typing import Dict, Iterable, List, Optional

import numpy as np

from biome_lab.config.schemas import DiseaseState
from biome_lab.entities.creatures import BehaviorState, Creature
from biome_lab.metrics.time_series import TimeSeries
from biome_lab.simulation.events import DeathCause, EventKind, SimulationEvent


class MetricsCollector:
    def __init__(self, window_seconds: float, mode: str = "full") -> None:
        if mode not in {"full", "light"}:
            raise ValueError("unknown metrics mode: %s" % mode)
        self.window_seconds = window_seconds
        self.mode = mode
        self.series = TimeSeries()
        self.events: List[SimulationEvent] = []
        self._last_sample_time: Optional[float] = None

    @property
    def rows(self) -> List[Dict[str, float]]:
        return self.series.rows

    def record_events(self, events: Iterable[SimulationEvent]) -> None:
        self.events.extend(events)

    def sample(self, world, interval_seconds: float = 1.0, force: bool = False) -> Optional[Dict[str, float]]:
        if self._last_sample_time is not None and not force:
            if world.time - self._last_sample_time < interval_seconds:
                return None

        herbivores: List[Creature] = []
        herbivore_energy = 0.0
        for creature in world.herbivores:
            if creature.alive:
                herbivores.append(creature)
                herbivore_energy += creature.energy
        predators: List[Creature] = []
        predator_energy = 0.0
        for creature in world.predators:
            if creature.alive:
                predators.append(creature)
                predator_energy += creature.energy
        plant_count = 0
        plant_energy = 0.0
        for plant in world.plants:
            if plant.alive:
                plant_count += 1
                plant_energy += plant.energy
        herbivore_count = len(herbivores)
        predator_count = len(predators)

        row: Dict[str, float] = {
            "time": round(world.time, 4),
            "population_plants": float(plant_count),
            "population_herbivores": float(herbivore_count),
            "population_predators": float(predator_count),
            "resources_available_energy": float(plant_energy),
            "mean_energy_herbivores": self._mean_from_total(herbivore_energy, herbivore_count),
            "mean_energy_predators": self._mean_from_total(predator_energy, predator_count),
        }
        if self.mode == "light":
            self.series.append(row)
            self._last_sample_time = world.time
            return row

        row.update(
            {
            "deaths_herbivores_total": float(self._death_count_by_species("herbivore")),
            "deaths_predators_total": float(self._death_count_by_species("predator")),
            "deaths_famine_total": float(self._death_count(DeathCause.FAMINE)),
            "deaths_disease_total": float(self._death_count(DeathCause.DISEASE)),
            "deaths_predation_total": float(self._death_count(DeathCause.PREDATION)),
            "deaths_old_age_total": float(self._death_count(DeathCause.OLD_AGE)),
            "death_rate_herbivores_window": self._death_rate(world.time, species="herbivore"),
            "death_rate_predators_window": self._death_rate(world.time, species="predator"),
            "death_rate_famine_window": self._death_rate(world.time, cause=DeathCause.FAMINE),
            "death_rate_disease_window": self._death_rate(world.time, cause=DeathCause.DISEASE),
            "death_rate_predation_window": self._death_rate(world.time, cause=DeathCause.PREDATION),
            "death_rate_old_age_window": self._death_rate(world.time, cause=DeathCause.OLD_AGE),
            "infection_rate_window": self._event_rate(EventKind.INFECTION, world.time),
            "mutation_rate_window": self._event_rate(EventKind.MUTATION, world.time),
            "predation_rate_window": self._event_rate(EventKind.PREDATION, world.time),
            "reproduction_rate_herbivores_window": self._event_rate(EventKind.BIRTH, world.time, species="herbivore"),
            "reproduction_rate_predators_window": self._event_rate(EventKind.BIRTH, world.time, species="predator"),
            "mean_survival_time_herbivores": self._mean_survival_time("herbivore"),
            "mean_survival_time_predators": self._mean_survival_time("predator"),
            "infected_herbivores": float(self._infected_count(herbivores)),
            "infected_predators": float(self._infected_count(predators)),
            "mean_generation_herbivores": self._mean_attribute(herbivores, "generation"),
            "mean_generation_predators": self._mean_attribute(predators, "generation"),
            "mean_mutation_count_herbivores": self._mean_attribute(herbivores, "mutation_count"),
            "mean_mutation_count_predators": self._mean_attribute(predators, "mutation_count"),
            "season_index": float(getattr(world, "current_season_index", lambda: -1)()),
            }
        )
        if hasattr(world, "topology_summary"):
            topology = world.topology_summary()
            row["topology_enabled"] = topology["enabled"]
            row["terrain_min_elevation"] = topology["min_elevation"]
            row["terrain_max_elevation"] = topology["max_elevation"]
            row["terrain_mean_elevation"] = topology["mean_elevation"]
            row["terrain_roughness"] = topology["roughness"]
        row["population_variance_herbivores_window"] = self._population_variance(
            "population_herbivores",
            herbivore_count,
            world.time,
        )
        row["population_variance_predators_window"] = self._population_variance(
            "population_predators",
            predator_count,
            world.time,
        )
        row.update(self._behavior_shares("herbivore", herbivores))
        row.update(self._behavior_shares("predator", predators))

        self.series.append(row)
        self._last_sample_time = world.time
        return row

    def latest(self) -> Optional[Dict[str, float]]:
        return self.series.latest()

    def death_counts_by_species(self) -> Dict[str, int]:
        counts = {"herbivore": 0, "predator": 0}
        for event in self.events:
            if event.kind == EventKind.DEATH:
                counts[event.species] = counts.get(event.species, 0) + 1
        return counts

    def death_counts_by_cause(self) -> Dict[str, int]:
        counts = {cause.value: 0 for cause in DeathCause}
        for event in self.events:
            if event.kind == EventKind.DEATH and event.cause is not None:
                counts[event.cause.value] = counts.get(event.cause.value, 0) + 1
        return counts

    def _mean_energy(self, creatures: List[Creature]) -> float:
        if not creatures:
            return 0.0
        return float(sum(creature.energy for creature in creatures) / len(creatures))

    def _mean_from_total(self, total: float, count: int) -> float:
        return 0.0 if count <= 0 else float(total / count)

    def _mean_attribute(self, creatures: List[Creature], attribute: str) -> float:
        if not creatures:
            return 0.0
        return float(sum(float(getattr(creature, attribute, 0.0)) for creature in creatures) / len(creatures))

    def _infected_count(self, creatures: List[Creature]) -> int:
        return sum(
            1
            for creature in creatures
            if getattr(creature, "disease_state", DiseaseState.SUSCEPTIBLE) == DiseaseState.INFECTED
        )

    def _death_count(self, cause: DeathCause) -> int:
        return sum(1 for event in self.events if event.kind == EventKind.DEATH and event.cause == cause)

    def _death_count_by_species(self, species: str) -> int:
        return sum(1 for event in self.events if event.kind == EventKind.DEATH and event.species == species)

    def _death_rate(
        self,
        now: float,
        species: Optional[str] = None,
        cause: Optional[DeathCause] = None,
    ) -> float:
        since = now - self.window_seconds
        count = 0
        for event in self.events:
            if event.time < since or event.kind != EventKind.DEATH:
                continue
            if species is not None and event.species != species:
                continue
            if cause is not None and event.cause != cause:
                continue
            count += 1
        return float(count / max(self.window_seconds, 1.0))

    def _event_rate(self, kind: EventKind, now: float, species: Optional[str] = None) -> float:
        since = now - self.window_seconds
        count = 0
        for event in self.events:
            if event.time < since or event.kind != kind:
                continue
            if species is not None and event.species != species:
                continue
            count += 1
        span = max(self.window_seconds, 1.0)
        return float(count / span)

    def _mean_survival_time(self, species: str) -> float:
        ages = [
            event.age
            for event in self.events
            if event.kind == EventKind.DEATH and event.species == species and event.age is not None
        ]
        if not ages:
            return 0.0
        return float(np.mean(ages))

    def _population_variance(self, field: str, current_value: int, now: float) -> float:
        since = now - self.window_seconds
        values = [row[field] for row in self.rows if row["time"] >= since and field in row]
        values.append(float(current_value))
        if len(values) < 2:
            return 0.0
        return float(np.var(values))

    def _behavior_shares(self, species: str, creatures: List[Creature]) -> Dict[str, float]:
        totals: Dict[str, float] = {state.value: 0.0 for state in BehaviorState}
        for creature in creatures:
            for behavior, duration in creature.behavior_time.items():
                totals[behavior] = totals.get(behavior, 0.0) + duration
        total_time = sum(totals.values())
        values: Dict[str, float] = {}
        for behavior in totals:
            key = "behavior_share_%s_%s" % (species, behavior)
            values[key] = 0.0 if total_time <= 0.0 else float(totals[behavior] / total_time)
        return values
