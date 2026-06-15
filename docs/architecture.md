# Architecture

## Overview

`PB Wave Agent Hub` has two coordinated subsystems:

- a live paper-trading subsystem
- a snapshot-conditioned replay subsystem

Both subsystems share the same strategic idea:

- use a filtered leaderboard as the candidate universe
- use Binance perpetual market data as the execution context
- derive 1h structure and OI-based weakness signals
- execute short trades with explicit fee / slippage assumptions

## Live Subsystem

Core files:

- `scripts/pb_wave_collector.py`
- `scripts/pb_wave_paper_trader.py`
- `services/server.py`

### Responsibilities

`pb_wave_collector.py`

- fetches source market universe data
- filters stablecoins, wrapped assets, pegged assets, and malformed symbols
- keeps only Binance perp executable candidates
- syncs 1h kline and 1h OI context
- writes the current leaderboard snapshot

`pb_wave_paper_trader.py`

- loads the latest market snapshot
- computes live states from synced kline / OI data
- generates base and continuation short candidates
- runs three virtual books:
  - `PB5`
  - `PB7.5`
  - `PB10`
- applies fee / slippage costs
- manages open positions using TP1, trailing / profit-mode logic, timeout, and stop handling

`server.py`

- serves a lightweight read-only monitoring UI
- exposes live trader and market state through local HTTP endpoints

## Replay Subsystem

Core package:

- `src/pb_wave_agent_hub/`

### Responsibilities

Replay entrypoints:

- convert legacy snapshots
- build monthly snapshot manifests
- build history sync plans
- download 1h perp kline / OI history
- run batch replay

Replay engine:

- freezes a historical snapshot at time `T0`
- reconstructs symbol state from lookback data
- replays forward for a fixed horizon
- produces orders, equity curve, and summary files

## Why Snapshot-Conditioned Replay

The replay model deliberately fixes the candidate universe per snapshot.

This makes it easier to:

- explain signal decisions
- compare different strategy variants
- keep execution assumptions explicit
- make the system reproducible for external reviewers

It is not intended to pretend that historical ranking rotation is free.

## Extension Path: BSC / Agent Layer

This repository is intentionally modular.

Future BSC or `BNB AI Agent SDK` integration can wrap:

- leaderboard update tasks
- replay requests
- state inspection
- signal publishing

without changing the core live or replay logic.

