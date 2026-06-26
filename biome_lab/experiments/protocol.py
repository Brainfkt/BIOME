from __future__ import annotations

from biome_lab.config.schemas import BiomeLabPreset


def protocol_summary(preset: BiomeLabPreset) -> str:
    protocol = preset.protocol
    return (
        "Question: %s\nHypothese: %s\nVariable independante: %s\n"
        "Variables dependantes: %s\nSeed: %s\nRepetitions: %s"
        % (
            protocol.research_question,
            protocol.hypothesis,
            protocol.independent_variable,
            ", ".join(protocol.dependent_variables),
            protocol.seed,
            protocol.repetitions,
        )
    )

