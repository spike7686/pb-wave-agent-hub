# PB Wave Short Skill

## Name

`pb_wave_short_skill`

## Purpose

This skill converts crypto leaderboard snapshots into structured, replayable short-strategy specifications.

It uses:

- leaderboard snapshot inputs
- Binance perpetual 1h kline context
- Binance perpetual 1h open-interest context
- PB Wave short-entry / stop / target logic

The result is a machine-readable skill payload plus optional replay outputs.

## When To Use

Use this skill when you want to:

- evaluate a frozen market snapshot
- build short candidates with explicit entries and stops
- export a strategy-spec JSON payload
- run a replay over one or more snapshots

## Inputs

The skill accepts a replay config JSON.

Supported config shapes:

- single-snapshot replay config
- batch replay config

Examples:

- `configs/month_replay.minimal_example.json`
- `configs/month_replay.example.json`

## Outputs

Primary output:

- a JSON skill payload containing structured candidates and diagnostics

Optional outputs:

- batch replay summary CSV / JSON
- equity curve CSV / JSON
- per-snapshot summary / trades / equity files

## Local Entry Point

Unified local wrapper:

```bash
python3 scripts/run_skill.py export \
  --config configs/month_replay.minimal_example.json \
  --output data/examples/month_2026_05/skill_example.json
```

Replay wrapper:

```bash
python3 scripts/run_skill.py replay \
  --config configs/month_replay.minimal_example.json
```

## Workflow

1. Load snapshot config
2. Resolve snapshot, 1h kline, and 1h OI inputs
3. Rebuild per-symbol market state
4. Apply PB Wave base short-signal logic
5. Build strategy candidates with stop / target structure
6. Export structured JSON payload
7. Optionally run replay and write result artifacts

## Output Schema Summary

Top-level payload fields include:

- `skill_name`
- `skill_version`
- `snapshot_id`
- `captured_at_utc`
- `market`
- `universe_size`
- `state_count`
- `warning_count`
- `raw_candidate_count`
- `base_cluster_count`
- `candidate_count`
- `candidates`
- `warnings`
- `diagnostics_preview`

Each candidate includes:

- `symbol`
- `signal_symbol`
- `rank`
- `strategy_family`
- `signal_type`
- `entry_time_utc`
- `entry_price`
- `stop_price`
- `stop_pct`
- `tp1_price`
- `tp2_price`
- `tp1_ratio`
- `target_r_multiple`
- `features`
- `rationale`
- `blockers`

## Notes

- This skill wrapper does not replace the underlying strategy engine.
- The actual signal logic and replay logic remain in the Python codebase.
- The skill layer provides a standard interface for invoking that logic and exporting structured outputs.
