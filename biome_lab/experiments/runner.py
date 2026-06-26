from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from biome_lab.config.schemas import BiomeLabPreset
from biome_lab.metrics.collector import MetricsCollector
from biome_lab.simulation.world import World


@dataclass
class RepetitionResult:
    repetition: int
    seed: int
    collector: MetricsCollector


def preset_with_seed(preset: BiomeLabPreset, seed: int) -> BiomeLabPreset:
    data = preset.model_dump()
    data["simulation"]["seed"] = seed
    data["protocol"]["seed"] = seed
    return BiomeLabPreset.model_validate(data)


def run_repetitions(preset: BiomeLabPreset) -> List[MetricsCollector]:
    return [result.collector for result in run_repetition_results(preset)]


def run_repetition_results(
    preset: BiomeLabPreset,
    duration_seconds: Optional[float] = None,
    repetitions: Optional[int] = None,
    seed: Optional[int] = None,
) -> List[RepetitionResult]:
    detailed_results: List[RepetitionResult] = []
    base_seed = preset.protocol.seed if seed is None else seed
    run_count = preset.protocol.repetitions if repetitions is None else repetitions
    duration = preset.protocol.duration_seconds if duration_seconds is None else duration_seconds
    for repetition in range(run_count):
        run_preset = preset_with_seed(preset, base_seed + repetition)
        world = World(run_preset)
        collector = MetricsCollector(window_seconds=run_preset.simulation.metrics_window_seconds)
        collector.record_events(world.events)
        collector.sample(world, force=True)
        fixed_dt = run_preset.simulation.fixed_dt
        while world.time < duration:
            events = world.update(fixed_dt)
            collector.record_events(events)
            collector.sample(world, interval_seconds=run_preset.simulation.metrics_sample_interval)
        collector.sample(world, force=True)
        detailed_results.append(
            RepetitionResult(
                repetition=repetition + 1,
                seed=base_seed + repetition,
                collector=collector,
            )
        )
    return detailed_results


def summarize_repetitions(results: List[RepetitionResult]) -> List[Dict[str, float]]:
    summaries: List[Dict[str, float]] = []
    for result in results:
        latest = result.collector.latest() or {}
        summaries.append(
            {
                "repetition": float(result.repetition),
                "seed": float(result.seed),
                "final_time": float(latest.get("time", 0.0)),
                "final_population_plants": float(latest.get("population_plants", 0.0)),
                "final_population_herbivores": float(latest.get("population_herbivores", 0.0)),
                "final_population_predators": float(latest.get("population_predators", 0.0)),
                "total_deaths_herbivores": float(latest.get("deaths_herbivores_total", 0.0)),
                "total_deaths_predators": float(latest.get("deaths_predators_total", 0.0)),
                "total_deaths_disease": float(latest.get("deaths_disease_total", 0.0)),
                "mean_survival_time_herbivores": float(latest.get("mean_survival_time_herbivores", 0.0)),
                "mean_survival_time_predators": float(latest.get("mean_survival_time_predators", 0.0)),
                "predation_rate_window": float(latest.get("predation_rate_window", 0.0)),
                "infection_rate_window": float(latest.get("infection_rate_window", 0.0)),
                "extinct_herbivores": float(latest.get("population_herbivores", 0.0) <= 0.0),
                "extinct_predators": float(latest.get("population_predators", 0.0) <= 0.0),
            }
        )
    return summaries
