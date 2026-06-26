from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from biome_lab.simulation.spatial_index import SpatialIndex


def _entity(entity_id: int, x: float, y: float, alive: bool = True):
    return SimpleNamespace(id=entity_id, position=np.array([x, y], dtype=float), alive=alive)


def test_query_radius_matches_bruteforce_distance() -> None:
    rng = np.random.default_rng(123)
    entities = [
        _entity(index, float(position[0]), float(position[1]))
        for index, position in enumerate(rng.uniform(0.0, 500.0, size=(250, 2)))
    ]
    entities.append(_entity(999, 250.0, 250.0, alive=False))
    index = SpatialIndex(cell_size=32.0)
    index.rebuild(entities)
    query_position = np.array([240.0, 260.0], dtype=float)
    radius = 90.0

    indexed_ids = {entity.id for entity in index.query_radius(query_position, radius)}
    brute_force_ids = {
        entity.id
        for entity in entities
        if entity.alive and float(np.dot(entity.position - query_position, entity.position - query_position)) <= radius * radius
    }

    assert indexed_ids == brute_force_ids


def test_query_radius_includes_neighboring_cells_on_boundaries() -> None:
    entities = [
        _entity(1, 63.9, 10.0),
        _entity(2, 64.1, 10.0),
        _entity(3, 130.0, 10.0),
    ]
    index = SpatialIndex(cell_size=64.0)
    index.rebuild(entities)

    results = index.query_radius(np.array([64.0, 10.0], dtype=float), radius=1.0)

    assert {entity.id for entity in results} == {1, 2}


def test_query_radius_into_reuses_result_buffer() -> None:
    entities = [
        _entity(1, 10.0, 10.0),
        _entity(2, 15.0, 10.0),
        _entity(3, 200.0, 200.0),
    ]
    index = SpatialIndex(cell_size=32.0)
    index.rebuild(entities)
    sentinel = _entity(99, 0.0, 0.0)
    results = [sentinel]

    returned = index.query_radius_into(np.array([10.0, 10.0], dtype=float), radius=10.0, results=results)

    assert returned is results
    assert {entity.id for entity in results} == {1, 2}

    index.query_radius_into(
        np.array([200.0, 200.0], dtype=float),
        radius=1.0,
        results=results,
        clear=False,
    )

    assert {entity.id for entity in results} == {1, 2, 3}
