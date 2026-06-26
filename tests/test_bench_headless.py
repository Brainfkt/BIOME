from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.bench_headless import SCENARIOS, scenario_names


def test_benchmark_scenarios_include_large_headless_runs() -> None:
    assert scenario_names("all") == ["headless_1k", "headless_5k", "headless_10k"]
    assert SCENARIOS["headless_5k"] == 5_000
    assert SCENARIOS["headless_10k"] == 10_000


def test_benchmark_subprocess_outputs_json_and_profile(tmp_path) -> None:
    output_path = tmp_path / "bench.json"
    profile_path = tmp_path / "profile.txt"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/bench_headless.py",
            "--scenario",
            "headless_1k",
            "--steps",
            "1",
            "--warmup-steps",
            "1",
            "--output",
            str(output_path),
            "--profile",
            str(profile_path),
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
        capture_output=True,
        text=True,
    )

    document = json.loads(result.stdout)
    written_document = json.loads(output_path.read_text(encoding="utf-8"))
    benchmark = document["benchmarks"][0]

    assert document == written_document
    assert benchmark["scenario"] == "headless_1k"
    assert benchmark["initial_creatures"] == 1_000
    assert benchmark["steps"] == 1
    assert benchmark["warmup_steps"] == 1
    assert benchmark["steps_per_second"] > 0
    assert benchmark["target_steps_per_second"] > 0
    assert benchmark["target_peak_memory_mb"] > 0
    assert benchmark["target_update_seconds"] > 0
    assert isinstance(benchmark["meets_targets"], bool)
    assert profile_path.exists()
    assert "Biome Lab profile: headless_1k" in profile_path.read_text(encoding="utf-8")
