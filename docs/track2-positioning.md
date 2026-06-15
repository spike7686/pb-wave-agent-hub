# Track 2 Positioning

## Submission Track

This repository is positioned for:

- `Track 2: Strategy Skills`

It is **not** positioned as a Track 1 live on-chain execution agent.

## Why It Fits Track 2

Track 2 asks for:

- a CMC Skill
- that turns market data into a backtestable strategy specification
- without requiring a live execution layer

This repository already does exactly that in modular form:

- transforms leaderboard snapshots into a filtered candidate universe
- enriches candidates with 1h kline and 1h open-interest context
- produces short-strategy entry logic
- computes stop / target structure
- generates replayable order outputs
- supports batch backtesting

## Core Track 2 Framing

The right way to present this project is:

`Market data -> candidate ranking -> signal generation -> strategy spec -> replayable orders`

Not:

`Binance paper trading bot`

The paper trader exists as a validation surface, but the competition-facing value is the strategy skill layer.

## What Reviewers Should Notice

### Technical execution

- real signal generation logic
- explicit stop / target construction
- fee / slippage aware replay
- reproducible CLI workflow

### Originality

- strategy combines leaderboard-driven universe selection with perp-specific OI context
- not just a price-only crossover system

### Practical relevance

- clear downstream user: researchers, quant builders, signal analysts, or future execution agents
- clean path from historical replay to future autonomous execution

### Demo clarity

- snapshots can be imported
- history sync plans can be generated
- replay orders can be created from those snapshots
- the repository is structured for reproducibility

## Recommended Demo Message

“This project is a strategy skill engine. It converts crypto market leaderboard snapshots into a structured, backtestable short-strategy specification with explicit entries, stops, targets, and replay outputs.”

## What To Avoid In The Pitch

Avoid framing this as:

- a finished live BSC execution agent
- an on-chain portfolio manager
- a production brokerage system

Those belong to a future Track 1-style extension, not to the current submission.

