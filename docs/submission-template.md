# Submission Template

## Project Name

PB Wave Agent Hub

## One-Line Summary

PB Wave Agent Hub is a Track-2 strategy skill engine that transforms crypto leaderboard snapshots into backtestable short-strategy specifications using Binance perp kline and open-interest context.

## Track

Track 2: Strategy Skills

## What Problem It Solves

Many crypto strategy demos show signals without demonstrating:

- candidate selection discipline
- execution-aware market context
- reproducible replay
- transparent cost assumptions

This project addresses that gap by combining:

- filtered leaderboard construction
- perp-compatible candidate routing
- 1h structural weakness detection
- OI-based signal refinement
- virtual execution with fees and slippage

## Core Features

- live virtual paper trading for `PB5`, `PB7.5`, `PB10`
- read-only monitoring dashboard
- historical snapshot import
- monthly snapshot manifest generation
- Binance perp history sync plan generation
- batch replay that outputs orders and equity curves
- strategy-skill-style JSON export from historical snapshots

## Reproducibility

Public repository includes:

- source code
- setup instructions
- replay configs
- example snapshot samples
- minimal smoke test
- sample replay outputs

Reproducible workflow:

1. import or fetch snapshots
2. build manifest / sync plan
3. sync Binance perp 1h kline and OI history
4. run batch replay
5. inspect generated orders and summary files
6. export a strategy-skill JSON payload

## Demo Commands

```bash
python3 -m pip install -e .[dev]
PYTHONPATH=src python3 -m pb_wave_agent_hub.cli.run_batch_replay --config configs/month_replay.minimal_example.json
PYTHONPATH=src python3 -m pb_wave_agent_hub.cli.export_strategy_skill --config configs/month_replay.minimal_example.json --output data/examples/month_2026_05/skill_example.json
pytest tests/test_minimal_replay.py
```

## Demo Output

- `batch_summary.csv`: per-snapshot strategy summary
- `batch_summary.json`: replay summary payload
- `trades.json`: generated replay orders
- `equity_curve.json`: replay equity path
- `skill_example.json`: Track-2-style strategy skill payload

## Why It Fits Track 2

- it turns market data into a structured, replayable strategy specification
- it does not require a live execution layer
- it exposes the path from raw snapshot to candidate order spec clearly
- it supports backtesting and inspection

## Notes

- no token issuance
- no fundraising
- no liquidity event
- research / virtual trading only
