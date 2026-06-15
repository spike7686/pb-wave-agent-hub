# Skill Usage

## Overview

This repository includes a thin skill wrapper around the existing PB Wave replay and signal-export logic.

The goal is to expose one clear interface for:

- exporting a structured skill payload
- running replay over snapshot bundles

## Files

Main skill-facing files:

- `SKILL.md`
- `scripts/run_skill.py`
- `src/pb_wave_agent_hub/cli/export_strategy_skill.py`
- `src/pb_wave_agent_hub/cli/run_batch_replay.py`

## Export A Skill Payload

```bash
python3 scripts/run_skill.py export \
  --config configs/month_replay.minimal_example.json \
  --output data/examples/month_2026_05/skill_example.json
```

This writes:

- `data/examples/month_2026_05/skill_example.json`

## Run Replay

```bash
python3 scripts/run_skill.py replay \
  --config configs/month_replay.minimal_example.json
```

This writes replay outputs under:

- `data/examples/month_2026_05/runs_min/`

## Recommended Minimal Validation

```bash
python3 -m pip install -e '.[dev]'
python3 scripts/run_skill.py replay --config configs/month_replay.minimal_example.json
python3 scripts/run_skill.py export --config configs/month_replay.minimal_example.json --output data/examples/month_2026_05/skill_example.json
pytest tests/test_minimal_replay.py
```

## Why This Wrapper Exists

The repository already had working replay and export logic.

This wrapper exists to make the project easier to understand as a reusable skill-style workflow without replacing the existing strategy engine.
