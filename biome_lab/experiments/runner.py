from __future__ import annotations

from typing import List

from biome_lab.config.schemas import BiomeLabPreset
from biome_lab.metrics.collector import MetricsCollector
from biome_lab.simulation.world import World


def preset_with_seed(preset: BiomeLabPreset, seed: int) -> BiomeLabPreset:
    data = preset.model_dump()
    data["simulation"]["seed"] = seed
    data["protocol"]["seed"] = seed
    return BiomeLabPreset.model_validate(data)


def run_repetitions(preset: BiomeLabPreset) -> List[MetricsCollector]:
    results: List[MetricsCollector] = []
    base_seed = preset.protocol.seed
    for repetition in range(preset.protocol.repetitions):
        run_preset = preset_with_seed(preset, base_seed + repetition)
        world = World(run_preset)
        collector = MetricsCollector(window_seconds=run_preset.simulation.metrics_window_seconds)
        collector.sample(world, force=True)
        fixed_dt = run_preset.simulation.fixed_dt
        while world.time < run_preset.protocol.duration_seconds:
            events = world.update(fixed_dt)
            collector.record_events(events)
            collector.sample(world, interval_seconds=run_preset.simulation.metrics_sample_interval)
        results.append(collector)
    return results
