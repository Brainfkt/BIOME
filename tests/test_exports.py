from __future__ import annotations

from biome_lab.config.defaults import create_default_preset
from biome_lab.exports.markdown_export import build_protocol_markdown


def test_protocol_markdown_contains_metric_and_parameter_definitions() -> None:
    markdown = build_protocol_markdown(create_default_preset(), rows=[])

    assert "Definitions des metriques" in markdown
    assert "Taux de predation" in markdown
    assert "hunger_threshold" in markdown

