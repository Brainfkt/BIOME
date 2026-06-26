from __future__ import annotations

import argparse
from pathlib import Path

from biome_lab.config.defaults import create_default_preset
from biome_lab.main import load_preset, load_simulation_document, run_headless
from biome_lab.simulation.world import World


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


def test_load_simulation_document_detects_world_state(tmp_path) -> None:
    state_path = tmp_path / "sandbox_state.json"
    World(create_default_preset()).to_world_state().save_json(state_path)

    document_type, document = load_simulation_document(state_path)

    assert document_type == "world_state"
    assert document.document_type == "world_state"
    assert load_preset(state_path).name == create_default_preset().name


def test_headless_run_can_start_from_world_state(tmp_path) -> None:
    state_path = tmp_path / "sandbox_state.json"
    World(create_default_preset()).to_world_state().save_json(state_path)
    args = argparse.Namespace(
        preset=state_path,
        output_dir=tmp_path,
        duration=0.1,
        repetitions=1,
        seed=None,
    )

    output_dir = run_headless(args)

    assert (output_dir / "preset.json").exists()
    assert (output_dir / "metrics.csv").exists()
    assert (output_dir / "events.csv").exists()


def test_headless_run_rejects_invalid_duration(tmp_path) -> None:
    args = argparse.Namespace(
        preset=None,
        output_dir=tmp_path,
        duration=0.0,
        repetitions=1,
        seed=None,
    )

    try:
        run_headless(args)
    except ValueError as exc:
        assert "--duration" in str(exc)
    else:
        raise AssertionError("invalid duration should be rejected")


def test_headless_run_rejects_invalid_repetitions(tmp_path) -> None:
    args = argparse.Namespace(
        preset=None,
        output_dir=tmp_path,
        duration=0.1,
        repetitions=0,
        seed=None,
    )

    try:
        run_headless(args)
    except ValueError as exc:
        assert "--repetitions" in str(exc)
    else:
        raise AssertionError("invalid repetitions should be rejected")
