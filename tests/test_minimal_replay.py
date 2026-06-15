from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "configs" / "month_replay.minimal_example.json"
RUNS_DIR = ROOT / "data" / "examples" / "month_2026_05" / "runs_min"
SKILL_OUTPUT = ROOT / "data" / "examples" / "month_2026_05" / "skill_example.json"


def run_module(*args: str) -> subprocess.CompletedProcess[str]:
    env = {"PYTHONPATH": str(ROOT / "src")}
    return subprocess.run(
        [sys.executable, "-m", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )


def test_minimal_batch_replay_smoke():
    result = run_module("pb_wave_agent_hub.cli.run_batch_replay", "--config", str(CONFIG_PATH))
    assert "batch_summary.csv" in result.stdout

    summary_csv = RUNS_DIR / "batch_summary.csv"
    summary_json = RUNS_DIR / "batch_summary.json"
    assert summary_csv.exists()
    assert summary_json.exists()

    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    assert len(payload) == 4
    assert payload[-1]["snapshot_id"] == "20260531T231504Z"
    assert "strategies" in payload[-1]


def test_strategy_skill_export_smoke():
    result = run_module(
        "pb_wave_agent_hub.cli.export_strategy_skill",
        "--config",
        str(CONFIG_PATH),
        "--output",
        str(SKILL_OUTPUT),
    )
    assert "skill_example.json" in result.stdout

    payload = json.loads(SKILL_OUTPUT.read_text(encoding="utf-8"))
    assert payload["skill_name"] == "pb_wave_short_skill"
    assert payload["market"] == "binance_perp"
    assert "warnings" in payload
    assert "diagnostics_preview" in payload
