from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from biome_lab.config.schemas import BiomeLabPreset


def save_preset_json(preset: BiomeLabPreset, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(preset.to_json(), encoding="utf-8")
    return path


def save_json_document(document: Dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    return path
