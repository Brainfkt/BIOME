from __future__ import annotations

from typing import List, Optional

from biome_lab.config.defaults import create_default_preset
from biome_lab.config.schemas import BiomeLabPreset
from biome_lab.metrics.collector import MetricsCollector
from biome_lab.simulation.events import SimulationEvent
from biome_lab.simulation.world import World


class SimulationEngine:
    def __init__(self, preset: Optional[BiomeLabPreset] = None) -> None:
        self.preset = preset or create_default_preset()
        self.world = World(self.preset)
        self.metrics = MetricsCollector(window_seconds=self.preset.simulation.metrics_window_seconds)
        self.metrics.sample(self.world, force=True)
        self.paused = True
        self.speed_multiplier = 1.0
        self._accumulator = 0.0
        self.max_steps_per_frame = 10

    def reset(self, preset: Optional[BiomeLabPreset] = None) -> None:
        if preset is not None:
            self.preset = preset
        self.world = World(self.preset)
        self.metrics = MetricsCollector(window_seconds=self.preset.simulation.metrics_window_seconds)
        self.metrics.sample(self.world, force=True)
        self._accumulator = 0.0

    def toggle_pause(self) -> None:
        self.paused = not self.paused

    def set_paused(self, paused: bool) -> None:
        self.paused = paused

    def adjust_speed(self, factor: float) -> None:
        self.speed_multiplier = max(0.1, min(8.0, self.speed_multiplier * factor))

    def update(self, real_dt: float) -> List[SimulationEvent]:
        if self.paused:
            return []
        fixed_dt = self.preset.simulation.fixed_dt
        self._accumulator += min(real_dt * self.speed_multiplier, 1.0)
        all_events: List[SimulationEvent] = []
        steps = 0
        while self._accumulator >= fixed_dt and steps < self.max_steps_per_frame:
            events = self.world.update(fixed_dt)
            self.metrics.record_events(events)
            self.metrics.sample(
                self.world,
                interval_seconds=self.preset.simulation.metrics_sample_interval,
            )
            all_events.extend(events)
            self._accumulator -= fixed_dt
            steps += 1
            if self.world.time >= self.preset.protocol.duration_seconds:
                self.paused = True
                self._accumulator = 0.0
                break
        if steps >= self.max_steps_per_frame and self._accumulator >= fixed_dt:
            self._accumulator = fixed_dt
        return all_events
