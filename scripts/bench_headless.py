from __future__ import annotations

import argparse
import cProfile
import io
import json
import pstats
import time
import tracemalloc
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from biome_lab.config.defaults import create_default_preset
from biome_lab.config.schemas import BiomeLabPreset
from biome_lab.simulation.world import World


SCENARIOS: Dict[str, int] = {
    "headless_1k": 1_000,
    "headless_5k": 5_000,
    "headless_10k": 10_000,
}


def scenario_names(selected: str) -> List[str]:
    if selected == "all":
        return list(SCENARIOS)
    if selected not in SCENARIOS:
        raise ValueError("unknown benchmark scenario: %s" % selected)
    return [selected]


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


def _run_update_loop(world: World, fixed_dt: float, steps: int) -> int:
    event_count = 0
    for _ in range(steps):
        event_count += len(world.update(fixed_dt))
    return event_count


def _profile_report(profile: cProfile.Profile, scenario: str, steps: int) -> str:
    stream = io.StringIO()
    stream.write("Biome Lab profile: %s (%s measured steps)\n" % (scenario, steps))
    stats = pstats.Stats(profile, stream=stream)
    stats.strip_dirs().sort_stats("cumtime").print_stats(40)
    return stream.getvalue()


def run_benchmark(args: argparse.Namespace, scenario: str) -> Tuple[Dict[str, object], Optional[str]]:
    preset = build_preset(scenario, args.seed, args.dt, args.steps)

    tracemalloc.start()
    setup_start = time.perf_counter()
    world = World(preset)
    setup_seconds = time.perf_counter() - setup_start

    if args.warmup_steps > 0:
        _run_update_loop(world, preset.simulation.fixed_dt, args.warmup_steps)
        world.events.clear()

    profile: Optional[cProfile.Profile] = cProfile.Profile() if args.profile is not None else None
    update_start = time.perf_counter()
    if profile is None:
        event_count = _run_update_loop(world, preset.simulation.fixed_dt, args.steps)
    else:
        profile.enable()
        event_count = _run_update_loop(world, preset.simulation.fixed_dt, args.steps)
        profile.disable()
    update_seconds = time.perf_counter() - update_start
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    result = {
        "scenario": scenario,
        "seed": args.seed,
        "steps": args.steps,
        "warmup_steps": args.warmup_steps,
        "fixed_dt": preset.simulation.fixed_dt,
        "simulated_seconds": round(world.time, 6),
        "measured_simulated_seconds": round(args.steps * preset.simulation.fixed_dt, 6),
        "initial_creatures": preset.simulation.initial_herbivores + preset.simulation.initial_predators,
        "final_creatures": world.living_creature_count(),
        "plants": sum(1 for plant in world.plants if plant.alive),
        "events": event_count,
        "setup_seconds": round(setup_seconds, 6),
        "update_seconds": round(update_seconds, 6),
        "steps_per_second": 0.0 if update_seconds <= 0.0 else round(args.steps / update_seconds, 3),
        "peak_memory_mb": round(peak_bytes / (1024 * 1024), 3),
    }
    profile_text = None if profile is None else _profile_report(profile, scenario, args.steps)
    return result, profile_text


def run_benchmarks(args: argparse.Namespace) -> Dict[str, object]:
    results: List[Dict[str, object]] = []
    profile_sections: List[str] = []
    for scenario in scenario_names(args.scenario):
        result, profile_text = run_benchmark(args, scenario)
        results.append(result)
        if profile_text is not None:
            profile_sections.append(profile_text)

    document: Dict[str, object] = {
        "benchmarks": results,
        "profile_path": None if args.profile is None else str(args.profile),
    }
    if args.profile is not None:
        args.profile.parent.mkdir(parents=True, exist_ok=True)
        args.profile.write_text("\n\n".join(profile_sections), encoding="utf-8")
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run reproducible Biome Lab headless benchmarks.")
    parser.add_argument("--scenario", choices=["all"] + list(SCENARIOS), default="headless_1k")
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--warmup-steps", type=int, default=0)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--dt", type=float, default=0.05)
    parser.add_argument("--output", type=Path, help="optional JSON output path")
    parser.add_argument("--profile", type=Path, help="optional cProfile text report path")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.steps <= 0:
        parser.error("--steps must be greater than 0")
    if args.warmup_steps < 0:
        parser.error("--warmup-steps must be greater than or equal to 0")
    if args.dt <= 0.0 or args.dt > 0.25:
        parser.error("--dt must be in the interval ]0, 0.25]")
    print(json.dumps(run_benchmarks(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
