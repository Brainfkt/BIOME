from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional


def load_preset(path: Optional[Path] = None):
    from biome_lab.config.defaults import create_default_preset
    from biome_lab.config.schemas import BiomeLabPreset

    if path is None:
        return create_default_preset()
    return BiomeLabPreset.from_json_path(path)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="biome-lab",
        description="Biome Lab: simulateur agent-based scientifique et pedagogique.",
    )
    subparsers = parser.add_subparsers(dest="command")

    ui_parser = subparsers.add_parser("ui", help="lancer l'interface Pygame")
    ui_parser.add_argument("--preset", type=Path, help="chemin vers un preset JSON")

    run_parser = subparsers.add_parser("run", help="lancer une experience headless")
    run_parser.add_argument("--preset", type=Path, help="chemin vers un preset JSON")
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
            }
        )
    return rows


def run_headless(args: argparse.Namespace) -> Path:
    from biome_lab.experiments.runner import run_repetition_results, summarize_repetitions
    from biome_lab.exports.csv_export import save_rows_csv
    from biome_lab.exports.json_export import save_json_document, save_preset_json

    preset = load_preset(args.preset)
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

    preset = load_preset(getattr(args, "preset", None))
    app = BiomeLabApp(preset)
    app.run()


def main(argv: Optional[list[str]] = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command in (None, "ui"):
        run_ui(args)
        return
    if args.command == "run":
        output_dir = run_headless(args)
        print("Exported headless run to %s" % output_dir)
        return
    parser.error("unknown command: %s" % args.command)


if __name__ == "__main__":
    main()
