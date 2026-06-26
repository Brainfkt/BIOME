from __future__ import annotations

import argparse
import json
import time
import tracemalloc
from typing import Dict

from biome_lab.config.defaults import create_default_preset
from biome_lab.config.schemas import BiomeLabPreset
from biome_lab.simulation.world import World


SCENARIOS: Dict[str, int] = {
    "headless_1k": 1_000,
    "headless_5k": 5_000,
    "headless_10k": 10_000,
}


def build_preset(scenario: str, seed: int, fixed_dt: float, steps: int) -> BiomeLabPreset:
    creature_count = SCENARIOS[scenario]
    herbivore_count = int(creature_count * 0.8)
    predator_count = creature_count - herbivore_count
    plant_count = max(100, creature_count // 4)
    world_width = max(1_600, int(creature_count * 0.7))
    world_height = max(1_000, int(world_width * 0.65))

    data = create_default_preset().model_dump()
    data["name"] = scenario
    simulation = data["simulation"]
    simulation.update(
        {
            "world_width": world_width,
            "world_height": world_height,
            "initial_herbivores": herbivore_count,
            "initial_predators": predator_count,
            "max_creatures": creature_count,
            "fixed_dt": fixed_dt,
            "seed": seed,
            "initial_energy_max_fraction": 0.60,
            "plant": {
                **simulation["plant"],
                "initial_count": plant_count,
                "max_count": plant_count,
                "regrowth_per_second": 0.0,
            },
            "environment": {
                "obstacles": [],
                "zones": [],
            },
            "topology": {
                **simulation["topology"],
                "enabled": False,
                "features": [],
            },
            "seasons": {
                **simulation["seasons"],
                "enabled": False,
            },
            "disease": {
                **simulation["disease"],
                "enabled": False,
                "initial_infected": 0,
            },
            "mutation": {
                **simulation["mutation"],
                "enabled": False,
            },
        }
    )
    data["protocol"]["duration_seconds"] = fixed_dt * steps
    data["protocol"]["repetitions"] = 1
    data["protocol"]["seed"] = seed
    return BiomeLabPreset.model_validate(data)


def run_benchmark(args: argparse.Namespace) -> Dict[str, object]:
    preset = build_preset(args.scenario, args.seed, args.dt, args.steps)

    tracemalloc.start()
    setup_start = time.perf_counter()
    world = World(preset)
    setup_seconds = time.perf_counter() - setup_start

    event_count = 0
    update_start = time.perf_counter()
    for _ in range(args.steps):
        event_count += len(world.update(preset.simulation.fixed_dt))
    update_seconds = time.perf_counter() - update_start
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "scenario": args.scenario,
        "seed": args.seed,
        "steps": args.steps,
        "fixed_dt": preset.simulation.fixed_dt,
        "simulated_seconds": round(world.time, 6),
        "initial_creatures": preset.simulation.initial_herbivores + preset.simulation.initial_predators,
        "final_creatures": world.living_creature_count(),
        "plants": sum(1 for plant in world.plants if plant.alive),
        "events": event_count,
        "setup_seconds": round(setup_seconds, 6),
        "update_seconds": round(update_seconds, 6),
        "steps_per_second": 0.0 if update_seconds <= 0.0 else round(args.steps / update_seconds, 3),
        "peak_memory_mb": round(peak_bytes / (1024 * 1024), 3),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run reproducible Biome Lab headless benchmarks.")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="headless_1k")
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--dt", type=float, default=0.05)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.steps <= 0:
        parser.error("--steps must be greater than 0")
    if args.dt <= 0.0 or args.dt > 0.25:
        parser.error("--dt must be in the interval ]0, 0.25]")
    print(json.dumps(run_benchmark(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
