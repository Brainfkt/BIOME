from __future__ import annotations

from biome_lab.metrics.collector import MetricsCollector
from biome_lab.simulation.events import DeathCause, EventKind, SimulationEvent


def test_event_rates_and_survival_time_are_scientific_metrics() -> None:
    collector = MetricsCollector(window_seconds=10.0)
    collector.record_events(
        [
            SimulationEvent(time=1.0, kind=EventKind.PREDATION, species="predator", entity_id=10, target_id=1),
            SimulationEvent(
                time=1.0,
                kind=EventKind.DEATH,
                species="herbivore",
                entity_id=1,
                cause=DeathCause.PREDATION,
                age=12.0,
            ),
            SimulationEvent(time=2.0, kind=EventKind.BIRTH, species="herbivore", entity_id=2, target_id=3),
        ]
    )

    assert collector._event_rate(EventKind.PREDATION, now=5.0) == 0.1
    assert collector._event_rate(EventKind.BIRTH, now=5.0, species="herbivore") == 0.1
    assert collector._mean_survival_time("herbivore") == 12.0


def test_death_counts_support_chart_modes() -> None:
    collector = MetricsCollector(window_seconds=10.0)
    collector.record_events(
        [
            SimulationEvent(
                time=1.0,
                kind=EventKind.DEATH,
                species="herbivore",
                entity_id=1,
                cause=DeathCause.PREDATION,
            ),
            SimulationEvent(
                time=2.0,
                kind=EventKind.DEATH,
                species="predator",
                entity_id=2,
                cause=DeathCause.FAMINE,
            ),
            SimulationEvent(
                time=3.0,
                kind=EventKind.DEATH,
                species="herbivore",
                entity_id=3,
                cause=DeathCause.OLD_AGE,
            ),
        ]
    )

    assert collector.death_counts_by_species() == {"herbivore": 2, "predator": 1}
    assert collector.death_counts_by_cause() == {
        "disease": 0,
        "famine": 1,
        "predation": 1,
        "old_age": 1,
    }
