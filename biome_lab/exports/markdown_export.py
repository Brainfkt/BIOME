from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from biome_lab.config.parameter_docs import METRIC_DOC_INTRO, PARAMETER_DOCS
from biome_lab.config.schemas import BiomeLabPreset
from biome_lab.metrics.definitions import METRIC_DEFINITIONS


def build_protocol_markdown(preset: BiomeLabPreset, rows: List[Dict[str, float]]) -> str:
    protocol = preset.protocol
    latest = rows[-1] if rows else {}
    lines = [
        "# Protocole experimental - Biome Lab",
        "",
        "## Question de recherche",
        protocol.research_question,
        "",
        "## Hypothese",
        protocol.hypothesis,
        "",
        "## Variables",
        "- Variable independante : %s" % protocol.independent_variable,
        "- Variables dependantes : %s" % ", ".join(protocol.dependent_variables),
        "- Parametres constants : %s" % ", ".join(protocol.constant_parameters),
        "",
        "## Reproductibilite",
        "- Duree simulee : %.1f s" % protocol.duration_seconds,
        "- Seed : %s" % protocol.seed,
        "- Repetitions prevues : %s" % protocol.repetitions,
        "",
        "## Definitions des metriques",
        METRIC_DOC_INTRO,
        "",
    ]
    for definition in METRIC_DEFINITIONS.values():
        lines.append("- **%s** : %s Utilite : %s" % (
            definition.name,
            definition.definition,
            definition.scientific_use,
        ))
    lines.extend(["", "## Definitions des parametres principaux", ""])
    for key, value in PARAMETER_DOCS.items():
        lines.append(
            "- **%s** : %s Role : %s Effet attendu : %s"
            % (key, value["definition"], value["role"], value["expected_effect"])
        )
    lines.extend(["", "## Resume du dernier etat", ""])
    if latest:
        for key in sorted(latest):
            lines.append("- %s : %s" % (key, latest[key]))
    else:
        lines.append("Aucune metrique echantillonnee.")
    if protocol.notes:
        lines.extend(["", "## Notes", protocol.notes])
    return "\n".join(lines) + "\n"


def save_protocol_markdown(preset: BiomeLabPreset, rows: List[Dict[str, float]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_protocol_markdown(preset, rows), encoding="utf-8")
    return path

