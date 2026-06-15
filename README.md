# PB Wave Agent Hub

Track target:

- `BNB Hack: AI Trading Agent Edition`
- `Track 2: Strategy Skills`

`PB Wave Agent Hub` is a clean submission repository extracted from the live-running `pb_wave_clean` stack and the offline `pb_rank_replay` research code.

For this hackathon, the repository is intentionally framed as a `Strategy Skill` project:

- ingest leaderboard snapshots
- enrich them with Binance perp 1h kline and 1h open-interest context
- produce structured short candidates with entry / stop / target fields
- replay those candidates forward into orders, PnL, and equity curves

This makes the project easy to judge on technical execution and reproducibility without pretending it is already a BSC live-trading agent.

## Repository Name

Recommended GitHub repository name:

- `pb-wave-agent-hub`

Alternative names:

- `pb-wave-bsc-agent`
- `pb-wave-perp-replay`
- `pb-wave-short-agent`

`pb-wave-agent-hub` is the best default because it is broad enough for:

- current live paper trader
- replay / backtest engine
- later BSC / BNB AI Agent SDK integration

## What This Project Does

This repository contains two linked workflows, but the competition-facing primary value is the `Strategy Skill` layer.

### 1. Live Workflow

The live workflow runs the current online strategy stack:

- collect a filtered Binance-perp-compatible leaderboard
- sync 1h perp klines and 1h open interest
- run virtual paper trading for:
  - `PB5`
  - `PB7.5`
  - `PB10`
- expose a lightweight read-only dashboard

Main files:

- `scripts/pb_wave_collector.py`
- `scripts/pb_wave_paper_trader.py`
- `services/server.py`

### 2. Replay Workflow

The replay workflow performs snapshot-conditioned historical backtesting:

1. load historical leaderboard snapshots
2. load matching 1h perp kline and 1h OI history
3. replay the PB Wave short strategy forward from each snapshot
4. generate trades, summaries, and equity curves

Main package:

- `src/pb_wave_agent_hub/`

### 3. Strategy Skill Workflow

For Track 2, the key output is:

- market snapshot in
- structured strategy candidates out
- replayable order specs out

This repository therefore supports exporting a strategy-skill-style payload from a historical snapshot and validating that payload with the replay engine.

## Why This Is Interesting

This system is not a generic price-only backtester.

It couples:

- leaderboard-based candidate discovery
- perp market execution context
- 1h structure-based short timing
- open-interest-aware weakness detection
- continuation logic
- fee and slippage aware virtual execution

The project therefore sits at the intersection of:

- market screening
- execution-aware virtual trading
- reproducible replay research

## Project Structure

```text
pb-wave-agent-hub/
  app/
  configs/
  data/
    snapshots/
    klines_1h/
    oi_1h/
    runs/
  docs/
  runtime/
  scripts/
  services/
  src/pb_wave_agent_hub/
```

## Quick Start

### Environment

Recommended:

- Python `3.10+`

Install package in editable mode:

```bash
cd /path/to/pb-wave-agent-hub
python3 -m pip install -e .
```

Install test dependency:

```bash
python3 -m pip install -e .[dev]
```

## Fastest Demo Path

If you want the shortest end-to-end proof that the repo works, run these three commands:

```bash
cd /path/to/pb-wave-agent-hub
PYTHONPATH=src python3 -m pb_wave_agent_hub.cli.run_batch_replay --config configs/month_replay.minimal_example.json
PYTHONPATH=src python3 -m pb_wave_agent_hub.cli.export_strategy_skill --config configs/month_replay.minimal_example.json --output data/examples/month_2026_05/skill_example.json
pytest tests/test_minimal_replay.py
```

Expected artifacts:

- `data/examples/month_2026_05/runs_min/batch_summary.csv`
- `data/examples/month_2026_05/runs_min/batch_summary.json`
- `data/examples/month_2026_05/skill_example.json`

## Live Paper Trader

Run one collector cycle:

```bash
cd /path/to/pb-wave-agent-hub
python3 scripts/pb_wave_collector.py
```

Run paper trader entry:

```bash
python3 scripts/pb_wave_paper_trader.py --mode entry_5m
```

Run paper trader manage:

```bash
python3 scripts/pb_wave_paper_trader.py --mode manage_1m
```

Run web dashboard:

```bash
python3 services/server.py
```

Then open:

- `http://127.0.0.1:8080`

## One-Month Replay Workflow

This repository supports a reproducible one-month workflow.

### Step 1. Convert legacy snapshots into replay format

If you already have legacy raw snapshots:

```bash
cd /path/to/pb-wave-agent-hub
PYTHONPATH=src python3 -m pb_wave_agent_hub.cli.import_legacy_snapshots \
  --input-dir /absolute/path/to/legacy/top15_tracker/snapshots/raw \
  --output-dir data/snapshots/month_2026_05 \
  --start-date 2026-05-01 \
  --end-date 2026-05-31
```

### Step 2. Build a snapshot manifest

```bash
PYTHONPATH=src python3 -m pb_wave_agent_hub.cli.build_snapshot_manifest \
  --snapshot-glob 'data/snapshots/month_2026_05/*.json' \
  --output data/snapshots/month_2026_05_manifest.json
```

### Step 3. Build a unified history sync plan

```bash
PYTHONPATH=src python3 -m pb_wave_agent_hub.cli.build_history_sync_plan \
  --snapshot-glob 'data/snapshots/month_2026_05/*.json' \
  --lookback-hours 240 \
  --forward-hours 168 \
  --output data/plans/month_2026_05_sync_plan.json
```

### Step 4. Download required Binance perp 1h kline and OI history

```bash
PYTHONPATH=src python3 -m pb_wave_agent_hub.cli.sync_binance_history_plan \
  --plan data/plans/month_2026_05_sync_plan.json \
  --kline-dir data/klines_1h \
  --oi-dir data/oi_1h
```

### Step 5. Run the batch replay

```bash
PYTHONPATH=src python3 -m pb_wave_agent_hub.cli.run_batch_replay \
  --config configs/month_replay.example.json
```

### Step 6. Read results

Output files:

- `data/runs/month_2026_05/batch_summary.csv`
- `data/runs/month_2026_05/batch_summary.json`
- `data/runs/month_2026_05/batch_equity_curve.csv`
- `data/runs/month_2026_05/batch_equity_curve.json`

Per-snapshot outputs:

- `summary.json`
- `trades.json`
- `equity_curve.json`

## Track 2 Skill Export

Export a strategy-skill-style JSON payload from one snapshot.

This command accepts either:

- a single-snapshot replay config
- a batch replay config, in which case it exports from the first snapshot in that config

Example using the bundled minimal batch config:

```bash
PYTHONPATH=src python3 -m pb_wave_agent_hub.cli.export_strategy_skill \
  --config configs/month_replay.minimal_example.json \
  --output data/examples/month_2026_05/skill_example.json
```

This produces a structured payload containing:

- filtered strategy candidates
- entry / stop / target fields
- feature context
- replay-friendly signal metadata

## Included Example Assets

This repository includes a lightweight example directory:

- `data/examples/month_2026_05/snapshots/`
- `data/examples/month_2026_05/snapshots_min/`
- `data/examples/month_2026_05/klines_1h_min/`
- `data/examples/month_2026_05/oi_1h_min/`

Purpose:

- show the expected folder structure
- provide a small inspection-friendly sample
- give reviewers a fast smoke-test dataset

Important:

- these example assets are **not** the full one-month reproducibility bundle
- they are primarily a `pipeline verification sample`
- some included example snapshots intentionally produce `0 trades` because the goal is to prove the replay and diagnostics pipeline, not to cherry-pick profitable examples
- the full replay workflow should still follow:
  - snapshot import / generation
  - history sync plan generation
  - Binance perp kline / OI sync
  - batch replay execution

## Test Entry

This repo includes a minimal smoke test:

```bash
pytest tests/test_minimal_replay.py
```

The smoke test verifies:

- the bundled minimal batch replay runs successfully
- summary artifacts are generated
- a strategy-skill JSON payload can be exported

## Included Strategy Books

This repository uses three risk books:

- `PB5`
- `PB7.5`
- `PB10`

These are the same three virtual books used by the live paper trading system.

## Cost Model

Replay and paper trading both use an explicit rough execution cost model:

- fee: `4 bps per side`
- slippage: `5 bps per side`

This is intentionally simple and transparent for reproducibility.

## Data Included / Data Submission Guidance

For public submission, do not commit large raw full-history datasets unless needed.

Recommended public submission contents:

- source code
- example configs
- small example snapshots
- sample replay inputs
- sample replay outputs
- setup instructions

Recommended release assets or external bundle contents:

- one-month snapshot set
- required 1h kline history
- required 1h OI history
- full replay outputs

This keeps the Git repository clean while preserving reproducibility.

## BNB AI Agent SDK Requirement

Current recommendation for this submission:

- it is **not necessary to block this repository on BNB AI Agent SDK integration**
- this project is already viable as a reproducible technical submission
- if the hackathon track or special award specifically rewards `BNB AI Agent SDK`, add it as an optional integration layer

Best practical framing:

- primary submission: this repository
- optional enhancement: add a `bsc_agent/` or `agent_sdk/` module that wraps leaderboard generation, replay triggers, or execution actions behind a BSC agent interface

## Suggested Next Step For Special Awards

If you want to optimize for BSC ecosystem fit, add one of:

- BSC on-chain strategy state anchoring
- BSC agent task orchestration
- BNB AI Agent SDK wrapper for leaderboard scanning and trade decision execution

That should be treated as an extension, not as a prerequisite for publishing this repository.

## License / Disclaimer

This is research and virtual trading software.

- no token sale
- no fundraising
- no liquidity bootstrapping
- no real-money promise

Use at your own risk.
