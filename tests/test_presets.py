from __future__ import annotations

from pathlib import Path

from biome_lab.config.defaults import create_default_preset
from biome_lab.config.schemas import BiomeLabPreset


def test_default_json_preset_matches_python_default() -> None:
    json_preset = BiomeLabPreset.from_json_path(Path("presets/default_experiment.json"))
    python_preset = create_default_preset()

    assert json_preset.model_dump(mode="json") == python_preset.model_dump(mode="json")


def test_preset_json_round_trip_can_reload(tmp_path) -> None:
    preset = create_default_preset()
    first_path = tmp_path / "preset.json"
    second_path = tmp_path / "preset_roundtrip.json"

    preset.save_json(first_path)
    exported = BiomeLabPreset.from_json_path(first_path)
    exported.save_json(second_path)
    reloaded = BiomeLabPreset.from_json_path(second_path)

    assert reloaded.model_dump(mode="json") == preset.model_dump(mode="json")
