from __future__ import annotations

import argparse

from pb_wave_agent_hub.config import load_batch_replay_config
from pb_wave_agent_hub.engines.replay import run_batch_snapshot_replay


def main():
    parser = argparse.ArgumentParser(description="Run batch snapshot-conditioned PB rank replay.")
    parser.add_argument("--config", required=True, help="Path to batch replay config JSON.")
    args = parser.parse_args()

    config = load_batch_replay_config(args.config)
    out = run_batch_snapshot_replay(config)
    print(out)


if __name__ == "__main__":
    main()
