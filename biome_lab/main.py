from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional, Tuple, Union

from pydantic import ValidationError

from biome_lab.config.schemas import BiomeLabPreset, WorldState


LoadedDocument = Union[BiomeLabPreset, WorldState]


def load_simulation_document(path: Optional[Path] = None) -> Tuple[str, LoadedDocument]:
    from biome_lab.config.defaults import create_default_preset

    if path is None:
        return "preset", create_default_preset()
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("top-level JSON document must be an object")
    document_type = data.get("document_type", "preset")
    if document_type == "world_state":
        return "world_state", WorldState.model_validate(data)
    if document_type == "preset":
        return "preset", BiomeLabPreset.model_validate(data)
    raise ValueError("unknown JSON document_type: %s" % document_type)


def load_preset(path: Optional[Path] = None) -> BiomeLabPreset:
    document_type, document = load_simulation_document(path)
    if document_type == "world_state":
        assert isinstance(document, WorldState)
        return document.preset
    assert isinstance(document, BiomeLabPreset)
    return document


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="biome-lab",
        description="Biome Lab: simulateur agent-based scientifique et pedagogique.",
    )
    subparsers = parser.add_subparsers(dest="command")

    ui_parser = subparsers.add_parser("ui", help="lancer l'interface Pygame")
    ui_parser.add_argument("--preset", type=Path, help="chemin vers un preset JSON ou un world_state JSON")

    run_parser = subparsers.add_parser("run", help="lancer une experience headless")
    run_parser.add_argument("--preset", type=Path, help="chemin vers un preset JSON ou un world_state JSON")
    run_parser.add_argument("--output-dir", type=Path, default=Path("exports"), help="dossier de sortie")
    run_parser.add_argument("--duration", type=float, help="duree simulee en secondes")
    run_parser.add_argument("--repetitions", type=int, help="nombre de repetitions")
    run_parser.add_argument("--seed", type=int, help="seed de depart")

    return parser


def _event_rows(events: Iterable[object], repetition: int, seed: int):
    rows = []
    for event in events:
        rows.append(
            {
                "repetition": repetition,
                "seed": seed,
                "time": event.time,
                "kind": event.kind.value,
                "species": event.species,
                "entity_id": event.entity_id,
                "target_id": event.target_id,
                "cause": None if event.cause is None else event.cause.value,
                "energy": event.energy,
                "age": event.age,
                "generation": event.generation,
                "mutation_count": event.mutation_count,
                "system": event.system,
                "enabled": event.enabled,
                "mutation_trait": event.mutation_trait,
                "old_value": event.old_value,
                "new_value": event.new_value,
            }
        )
    return rows


def _validate_run_overrides(args: argparse.Namespace) -> None:
    if args.duration is not None and args.duration <= 0:
        raise ValueError("--duration must be greater than 0 seconds")
    if args.repetitions is not None and args.repetitions <= 0:
        raise ValueError("--repetitions must be greater than 0")


def _run_world_state_once(state: WorldState, duration_seconds: Optional[float], seed: Optional[int]):
    from biome_lab.experiments.runner import RepetitionResult
    from biome_lab.metrics.collector import MetricsCollector
    from biome_lab.simulation.rng import create_rng
    from biome_lab.simulation.world import World

    world = World.from_world_state(state)
    if seed is not None:
        run_preset = world.preset.model_copy(deep=True)
        run_preset.simulation.seed = seed
        run_preset.protocol.seed = seed
        world.preset = run_preset
        world.config = run_preset.simulation
        world.rng = create_rng(seed)
    collector = MetricsCollector(window_seconds=world.preset.simulation.metrics_window_seconds)
    collector.record_events(world.events)
    collector.sample(world, force=True)
    if duration_seconds is None:
        target_time = max(world.time, world.preset.protocol.duration_seconds)
    else:
        target_time = world.time + duration_seconds
    while world.time < target_time:
        events = world.update(world.preset.simulation.fixed_dt)
        collector.record_events(events)
        collector.sample(world, interval_seconds=world.preset.simulation.metrics_sample_interval)
    collector.sample(world, force=True)
    return [
        RepetitionResult(
            repetition=1,
            seed=world.preset.simulation.seed,
            collector=collector,
        )
    ]


def run_headless(args: argparse.Namespace) -> Path:
    from biome_lab.experiments.runner import run_repetition_results, summarize_repetitions
    from biome_lab.exports.csv_export import save_rows_csv
    from biome_lab.exports.json_export import save_json_document, save_preset_json

    _validate_run_overrides(args)
    document_type, document = load_simulation_document(args.preset)
    if document_type == "world_state":
        if args.repetitions not in (None, 1):
            raise ValueError("world_state headless runs support only --repetitions 1")
        assert isinstance(document, WorldState)
        preset = document.preset
        if args.seed is not None:
            preset = preset.model_copy(deep=True)
            preset.simulation.seed = args.seed
            preset.protocol.seed = args.seed
            document = document.model_copy(update={"preset": preset})
        results = _run_world_state_once(document, args.duration, args.seed)
    else:
        assert isinstance(document, BiomeLabPreset)
        preset = document
        results = run_repetition_results(
            preset,
            duration_seconds=args.duration,
            repetitions=args.repetitions,
            seed=args.seed,
        )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir / ("%s_%s" % (stamp, preset.name))
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics_rows = []
    event_rows = []
    for result in results:
        for row in result.collector.rows:
            enriched = dict(row)
            enriched["repetition"] = result.repetition
            enriched["seed"] = result.seed
            metrics_rows.append(enriched)
        event_rows.extend(_event_rows(result.collector.events, result.repetition, result.seed))

    save_preset_json(preset, output_dir / "preset.json")
    save_rows_csv(metrics_rows, output_dir / "metrics.csv")
    save_rows_csv(event_rows, output_dir / "events.csv")
    save_rows_csv(summarize_repetitions(results), output_dir / "summary.csv")
    save_json_document(
        {
            "preset_name": preset.name,
            "schema_version": preset.schema_version,
            "duration_seconds": args.duration or preset.protocol.duration_seconds,
            "repetitions": args.repetitions or preset.protocol.repetitions,
            "seed": args.seed if args.seed is not None else preset.protocol.seed,
            "output_files": ["preset.json", "metrics.csv", "events.csv", "summary.csv", "metadata.json"],
        },
        output_dir / "metadata.json",
    )
    return output_dir


def run_ui(args: argparse.Namespace) -> None:
    try:
        from biome_lab.ui.app import BiomeLabApp
    except ModuleNotFoundError as exc:
        missing = exc.name or "dependency"
        raise SystemExit(
            "Missing dependency '%s'. Install the project with: python -m pip install -e \".[dev]\""
            % missing
        )

    document_type, document = load_simulation_document(getattr(args, "preset", None))
    if document_type == "world_state":
        assert isinstance(document, WorldState)
        app = BiomeLabApp(document.preset)
        app.load_world_state(document)
    else:
        assert isinstance(document, BiomeLabPreset)
        app = BiomeLabApp(document)
    app.run()


def main(argv: Optional[list[str]] = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command in (None, "ui"):
            run_ui(args)
            return
        if args.command == "run":
            output_dir = run_headless(args)
            print("Exported headless run to %s" % output_dir)
            return
    except (OSError, ValueError, ValidationError, json.JSONDecodeError) as exc:
        raise SystemExit("Biome Lab input error: %s" % exc)
    parser.error("unknown command: %s" % args.command)


if __name__ == "__main__":
    main()
