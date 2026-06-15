# Example Prompts

## Purpose

This file shows how to interact with the repository as if it were a reusable skill.

The prompts below are useful for:

- manual operator workflows
- agent wrappers
- MCP-style orchestration layers
- demo scenarios

## Natural-Language Prompts

### 1. Export A Structured Skill Payload

Prompt:

“Use the PB Wave short skill to export a structured short-signal payload from the minimal replay config. Save the output to `data/examples/month_2026_05/skill_example.json`.”

Expected action:

- run skill export
- produce structured JSON

## 2. Run Replay On The Bundled Sample

Prompt:

“Run replay on the bundled minimal snapshot sample and return the path to the batch summary CSV.”

Expected action:

- run batch replay
- write replay outputs under `data/examples/month_2026_05/runs_min/`

## 3. Validate The Exported Skill Payload

Prompt:

“Export a skill payload from the minimal replay config and confirm that the result contains `skill_name`, `candidate_count`, `warnings`, and `diagnostics_preview`.”

Expected action:

- export JSON
- inspect top-level fields

## 4. Explain A No-Trade Snapshot

Prompt:

“Replay the bundled minimal sample and explain why some snapshots produce zero trades.”

Expected action:

- run replay or inspect replay outputs
- explain that the sample is a pipeline-validation sample
- reference warnings / diagnostics where relevant

## 5. Generate A Replayable Short-Signal Spec

Prompt:

“Take the configured snapshot universe, rebuild market state from 1h kline and 1h OI data, and generate replayable PB Wave short candidates with entry, stop, and target fields.”

Expected action:

- run the PB Wave signal pipeline
- return structured candidate data

## CLI Equivalents

Export:

```bash
python3 scripts/run_skill.py export \
  --config configs/month_replay.minimal_example.json \
  --output data/examples/month_2026_05/skill_example.json
```

Replay:

```bash
python3 scripts/run_skill.py replay \
  --config configs/month_replay.minimal_example.json
```

## Suggested Demo Prompt

“Use PB Wave Short Skill to analyze the bundled minimal snapshot sample, export a structured short-signal payload, then run replay and summarize the resulting artifacts.”

## Notes

- These prompts assume local repository access.
- They do not replace the strategy engine.
- They provide a skill-like invocation surface for the existing replay framework.
