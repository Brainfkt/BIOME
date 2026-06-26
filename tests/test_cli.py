from __future__ import annotations

import argparse
from pathlib import Path

from biome_lab.config.defaults import create_default_preset
from biome_lab.main import load_preset, run_headless


def test_load_preset_from_json_path() -> None:
    preset = load_preset(Path("presets/default_experiment.json"))

    assert preset.name == create_default_preset().name
    assert preset.schema_version == 1


def test_headless_run_exports_json_and_csv(tmp_path) -> None:
    args = argparse.Namespace(
        preset=None,
        output_dir=tmp_path,
        duration=0.2,
        repetitions=1,
        seed=123,
    )

    output_dir = run_headless(args)

    assert (output_dir / "preset.json").exists()
    assert (output_dir / "metrics.csv").exists()
    assert (output_dir / "events.csv").exists()
    assert (output_dir / "summary.csv").exists()
    assert (output_dir / "metadata.json").exists()

