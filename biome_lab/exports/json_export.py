from __future__ import annotations

from pathlib import Path

from biome_lab.config.schemas import BiomeLabPreset


def save_preset_json(preset: BiomeLabPreset, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(preset.to_json(), encoding="utf-8")
    return path

