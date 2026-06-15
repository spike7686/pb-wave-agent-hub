from __future__ import annotations

import argparse

from pb_wave_agent_hub.config import load_replay_config
from pb_wave_agent_hub.engines.replay import run_snapshot_replay
from pb_wave_agent_hub.providers.local_files import LocalFilesProvider


def main():
    parser = argparse.ArgumentParser(description="Run snapshot-conditioned PB rank replay.")
    parser.add_argument("--config", required=True, help="Path to replay config JSON.")
    args = parser.parse_args()

    config = load_replay_config(args.config)
    provider = LocalFilesProvider(
        snapshot_path=config.snapshot_path,
        kline_dir=config.kline_dir,
        oi_dir=config.oi_dir,
    )
    out = run_snapshot_replay(config, provider)
    print(out["summary_path"])


if __name__ == "__main__":
    main()
