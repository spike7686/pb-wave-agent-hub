# Strategy Skill Schema

Language:

- English
- [简体中文](./strategy-skill-schema.zh-CN.md)

## Purpose

The goal of the strategy skill layer is to convert a fixed market snapshot into a structured, replayable trading specification.

This repository uses the following conceptual output shape.

## Top-Level Object

```json
{
  "skill_name": "pb_wave_short_skill",
  "skill_version": "0.1.0",
  "snapshot_id": "20260531T231504Z",
  "captured_at_utc": "2026-05-31T23:15:04+00:00",
  "market": "binance_perp",
  "universe_size": 15,
  "candidate_count": 3,
  "candidates": []
}
```

## Candidate Object

```json
{
  "symbol": "WLD",
  "signal_symbol": "WLDUSDT",
  "rank": 1,
  "strategy_family": "pb_wave_short",
  "signal_type": "base",
  "entry_time_utc": "2026-05-31T23:00:00+00:00",
  "entry_price": 1.2345,
  "stop_price": 1.2850,
  "stop_pct": 4.09,
  "tp1_price": 1.1840,
  "tp2_price": 1.0830,
  "tp1_ratio": 0.35,
  "target_r_multiple": 3.0,
  "features": {},
  "rationale": {},
  "blockers": []
}
```

## Feature Fields

Suggested included fields:

- `runup_24h_pct`
- `trend_7d_pct`
- `trend_7d_label`
- `trend_48h_label`
- `trend_24h_label`
- `retrace_from_peak_pct`
- `peak_age_hours`
- `breakout_margin_pct`
- `lower_high_gap_pct`
- `weakness_score`
- `oi_1h_pct`
- `oi_4h_pct`
- `oi_12h_pct`
- `oi_24h_pct`
- `oi_to_vol_ratio`
- `price_oi_divergence_4h`

## Rationale Fields

Suggested included fields:

- `entry_profile`
- `stop_profile`
- `exit_profile`
- `selection_variant`
- `summary`

## Why This Schema Matters

This structure is useful because it provides:

- machine-readable strategy outputs
- a clear bridge between raw market data and final order specs
- a format that can be replayed, inspected, and extended
