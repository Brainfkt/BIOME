from __future__ import annotations

from pathlib import Path

from biome_lab.config.defaults import create_default_preset
from biome_lab.config.schemas import BiomeLabPreset


def test_default_json_preset_matches_python_default() -> None:
    json_preset = BiomeLabPreset.from_json_path(Path("presets/default_experiment.json"))
    python_preset = create_default_preset()

    assert json_preset.model_dump(mode="json") == python_preset.model_dump(mode="json")

