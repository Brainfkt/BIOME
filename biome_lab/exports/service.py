from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict

from biome_lab.config.schemas import BiomeLabPreset
from biome_lab.exports.csv_export import save_metrics_csv
from biome_lab.exports.json_export import save_preset_json
from biome_lab.exports.markdown_export import save_protocol_markdown
from biome_lab.metrics.collector import MetricsCollector


@dataclass
class ExportResult:
    preset_path: Path
    metrics_path: Path
    protocol_path: Path


class ExportService:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir

    def export_all(self, preset: BiomeLabPreset, metrics: MetricsCollector) -> ExportResult:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = "%s_%s" % (stamp, preset.name)
        preset_path = save_preset_json(preset, self.output_dir / ("%s_preset.json" % stem))
        metrics_path = save_metrics_csv(metrics.rows, self.output_dir / ("%s_metrics.csv" % stem))
        protocol_path = save_protocol_markdown(
            preset,
            metrics.rows,
            self.output_dir / ("%s_protocol.md" % stem),
        )
        return ExportResult(
            preset_path=preset_path,
            metrics_path=metrics_path,
            protocol_path=protocol_path,
        )

