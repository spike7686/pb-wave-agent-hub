# SKILL.md

## name

`pb_wave_short_skill`

## description

PB Wave Short Skill converts crypto leaderboard snapshots into structured, replayable short-strategy specifications.

It combines:

- leaderboard snapshot inputs
- Binance perpetual 1h kline context
- Binance perpetual 1h open-interest context
- PB Wave short-entry, stop, and target logic

The output is a machine-readable skill payload plus optional replay artifacts.

## requires

- `python>=3.10`
- local repository checkout
- replay config JSON
- 1h kline and 1h OI data for referenced symbols

Optional:

- `pytest` for smoke-test validation

## inputs

This skill accepts a replay config JSON.

Supported config shapes:

- single-snapshot replay config
- batch replay config

Example config files:

- `configs/month_replay.minimal_example.json`
- `configs/month_replay.example.json`

Required logical inputs:

- snapshot path or snapshot glob
- kline directory
- oi directory
- output directory
- replay window settings
- strategy configuration

## tools

Primary local entrypoints:

- `scripts/run_skill.py export`
- `scripts/run_skill.py replay`

Underlying modules:

- `pb_wave_agent_hub.cli.export_strategy_skill`
- `pb_wave_agent_hub.cli.run_batch_replay`

Supporting files:

- `docs/skill-usage.md`
- `docs/strategy-skill-schema.md`
- `docs/example-prompts.md`

## outputs

Primary output:

- structured JSON skill payload

Optional outputs:

- batch replay summary CSV / JSON
- batch equity curve CSV / JSON
- per-snapshot summary JSON
- per-snapshot trades JSON
- per-snapshot equity curve JSON

## example commands

Export a skill payload:

```bash
python3 scripts/run_skill.py export \
  --config configs/month_replay.minimal_example.json \
  --output data/examples/month_2026_05/skill_example.json
```

Run replay:

```bash
python3 scripts/run_skill.py replay \
  --config configs/month_replay.minimal_example.json
```

## workflow

1. Load replay config
2. Resolve snapshot, kline, and OI inputs
3. Rebuild per-symbol market state
4. Apply PB Wave base short-signal logic
5. Build structured candidates with stop and target fields
6. Export structured JSON payload
7. Optionally run replay and write result artifacts

## example output shape

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

## validation prompts

Use these prompts or checks to validate the skill locally:

- “Export a structured short-signal payload from the minimal replay config.”
- “Run replay on the bundled minimal example and show the batch summary path.”
- “Confirm that the exported payload contains `skill_name`, `candidate_count`, and `diagnostics_preview`.”

More prompt examples:

- `docs/example-prompts.md`

Recommended local validation:

```bash
python3 -m pip install -e '.[dev]'
python3 scripts/run_skill.py replay --config configs/month_replay.minimal_example.json
python3 scripts/run_skill.py export --config configs/month_replay.minimal_example.json --output data/examples/month_2026_05/skill_example.json
pytest tests/test_minimal_replay.py
```

## notes

- This skill wrapper does not replace the underlying strategy engine.
- The actual signal logic and replay logic remain in the Python codebase.
- The skill layer provides a standard interface for invoking that logic and exporting structured outputs.
