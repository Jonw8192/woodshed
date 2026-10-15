"""Repeatable tests for the Woodshed Touch Transfer pipeline.
Run with: python -m pytest tests/ -q
or simply: python tests/test_pipeline.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline import (
    compute_usage_changes,
    propose_faab,
    score_opportunity,
    load_verified_data,
    run_pipeline,
)


def test_load_data():
    data = load_verified_data(2026)
    assert "player_stats" in data
    assert data["player_stats"].height > 0, "player_stats empty"
    print("test_load_data: PASS")


def test_score_and_faab():
    sample = {
        "target_share": 0.22,
        "wopr": 0.35,
        "targets": 8,
        "offense_pct": 0.72,
        "target_share_wow": 0.08,
        "report_status": None,
    }
    score, notes = score_opportunity(sample)
    assert score > 50, f"expected high score, got {score}"
    rng, why = propose_faab(score, "high")
    assert "$" in rng
    print(f"test_score_and_faab: PASS (score={score}, range={rng})")


def test_full_pipeline_sample():
    result = run_pipeline(season=2026, top_n=8)
    assert "validation" in result
    v = result["validation"]
    assert v["candidates"] > 0
    assert Path(v["draft_path"]).exists()
    assert Path(v["packet_path"]).exists()
    print("test_full_pipeline_sample: PASS")
    print(json.dumps(v, indent=2))


if __name__ == "__main__":
    test_load_data()
    test_score_and_faab()
    test_full_pipeline_sample()
    print("All tests passed.")
