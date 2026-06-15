# Demo Script

Language:

- English
- [简体中文](./demo-script.zh-CN.md)

## Goal

This script is designed for a short Track 2 demo.

Recommended duration:

- `3 to 5 minutes`

Core message:

- `PB Wave Agent Hub` turns leaderboard snapshots into structured, backtestable short-strategy specifications
- it is not just a dashboard
- it is not just a paper trader
- it is a reproducible strategy skill pipeline

## Demo Structure

Suggested order:

1. problem
2. pipeline
3. repo proof
4. generated outputs
5. why it fits Track 2

## Opening

Suggested spoken version:

“PB Wave Agent Hub is a Track 2 strategy skill project. It starts from crypto leaderboard snapshots, enriches them with Binance perpetual 1h price and open-interest context, and converts that market state into structured short-strategy specifications that can be replayed, inspected, and extended.”

## Problem Statement

Suggested spoken version:

“Many crypto trading demos show buy or sell signals, but they do not show how the candidate universe was selected, what execution market they assumed, or whether the result is reproducible. This project focuses on that missing middle layer.”

## What The System Does

Suggested spoken version:

“The system has two linked layers. The live layer collects a filtered perp-executable leaderboard and runs three virtual books: PB5, PB7.5, and PB10. The competition-facing layer freezes historical snapshots, rebuilds market context from 1-hour kline and open-interest data, generates structured signals, and replays them into orders and equity curves.”

## Show The Repository

Open:

- `README.md`
- `docs/track2-positioning.md`
- `docs/strategy-skill-schema.md`

Suggested spoken version:

“Here the repository is explicitly framed for Track 2. The goal is to produce a machine-readable strategy specification from market data, not to pretend that this is already a fully deployed on-chain execution agent.”

## Show The Minimal Reproducible Path

Open or mention:

- `configs/month_replay.minimal_example.json`
- `tests/test_minimal_replay.py`

Suggested spoken version:

“For reproducibility, I included a minimal sample dataset, a replay config, and a smoke test. Reviewers can run a batch replay, export a strategy skill JSON payload, and verify the outputs locally.”

Suggested commands:

```bash
python3 -m pip install -e '.[dev]'
PYTHONPATH=src python3 -m pb_wave_agent_hub.cli.run_batch_replay --config configs/month_replay.minimal_example.json
PYTHONPATH=src python3 -m pb_wave_agent_hub.cli.export_strategy_skill --config configs/month_replay.minimal_example.json --output data/examples/month_2026_05/skill_example.json
pytest tests/test_minimal_replay.py
```

## Show Generated Outputs

Open:

- `data/examples/month_2026_05/runs_min/batch_summary.csv`
- `data/examples/month_2026_05/skill_example.json`

Suggested spoken version:

“Here is the replay summary output, and here is the exported skill payload. The important point is that the repo does not stop at signal ideas. It produces structured outputs that can be inspected and replayed.”

## Explain Why Some Sample Snapshots Have Zero Trades

Suggested spoken version:

“The bundled minimal sample is a pipeline verification sample, not a cherry-picked PnL demo. Some example snapshots produce zero trades, which is expected. That is still useful because it proves the state reconstruction, filtering, diagnostics, and export path are all working.”

## Why It Fits Track 2

Suggested spoken version:

“This fits Track 2 because it transforms market data into a structured, backtestable strategy specification. It has explicit entries, stops, targets, diagnostics, and replay outputs. It does not depend on a live execution layer in order to be evaluated.”

## If Judges Ask About Track 1

Suggested answer:

“Track 1 would require an on-chain execution agent and wallet-driven trade execution on BSC. This repository is not claiming that today. Instead, it provides the strategy-skill layer that such an agent could call in the future.”

## If Judges Ask About Originality

Suggested answer:

“The novelty is not a single indicator. The novelty is the combination of leaderboard-based candidate discovery, perp-specific market routing, 1h structural weakness detection, open-interest context, and reproducible replay outputs.”

## If Judges Ask About Real-World Use

Suggested answer:

“A researcher or execution agent can use this as a screening and signal-spec layer. It is suitable as a pre-trade intelligence module, a replay research tool, or a future execution-agent decision engine.”

## Closing

Suggested spoken version:

“So the core value of PB Wave Agent Hub is that it makes this strategy inspectable and reproducible. Instead of only saying ‘here is a signal,’ it shows how the signal was built, how it is encoded, and how it can be replayed.”
