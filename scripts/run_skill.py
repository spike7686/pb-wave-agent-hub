from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def run_module(module: str, *args: str) -> int:
    cmd = [sys.executable, "-m", module, *args]
    result = subprocess.run(cmd, cwd=ROOT, env={**dict(), **{"PYTHONPATH": str(ROOT / "src")}})
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified local wrapper for PB Wave skill export and replay.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export", help="Export structured strategy-skill JSON from a replay config.")
    export_parser.add_argument("--config", required=True, help="Replay config JSON path.")
    export_parser.add_argument("--output", required=True, help="Output JSON path.")

    replay_parser = subparsers.add_parser("replay", help="Run batch replay from a batch replay config.")
    replay_parser.add_argument("--config", required=True, help="Batch replay config JSON path.")

    args = parser.parse_args()

    if args.command == "export":
        return run_module(
            "pb_wave_agent_hub.cli.export_strategy_skill",
            "--config",
            args.config,
            "--output",
            args.output,
        )
    if args.command == "replay":
        return run_module(
            "pb_wave_agent_hub.cli.run_batch_replay",
            "--config",
            args.config,
        )
    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
