from __future__ import annotations

import argparse
import json
from datetime import datetime
from datetime import timedelta
from pathlib import Path


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_snapshot_rows(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw.get("rows", []) if isinstance(raw, dict) else raw


def main():
    parser = argparse.ArgumentParser(description="Build a consolidated Binance history sync plan from many snapshots.")
    parser.add_argument("--snapshot-glob", required=True, help="For example data/snapshots/year_1/*.json")
    parser.add_argument("--lookback-hours", type=int, default=240)
    parser.add_argument("--forward-hours", type=int, default=168)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    project_dir = Path.cwd()
    snapshot_paths = sorted(project_dir.glob(args.snapshot_glob))
    if not snapshot_paths:
        raise SystemExit(f"no snapshots matched: {args.snapshot_glob}")

    signal_symbols = set()
    captured_at_values = []
    for path in snapshot_paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        captured_at = raw.get("captured_at_utc") if isinstance(raw, dict) else raw[0].get("captured_at_utc")
        if captured_at:
            captured_at_values.append(parse_dt(captured_at))
        for row in load_snapshot_rows(path):
            signal_symbol = str(row.get("signal_symbol") or row.get("binance_perp_symbol") or "").upper().strip()
            if signal_symbol:
                signal_symbols.add(signal_symbol)

    start_dt = min(captured_at_values) - timedelta(hours=args.lookback_hours)
    end_dt = max(captured_at_values) + timedelta(hours=args.forward_hours)
    payload = {
        "snapshot_glob": args.snapshot_glob,
        "snapshot_count": len(snapshot_paths),
        "signal_symbol_count": len(signal_symbols),
        "signal_symbols": sorted(signal_symbols),
        "start_utc": start_dt.isoformat(),
        "end_utc": end_dt.isoformat(),
        "lookback_hours": args.lookback_hours,
        "forward_hours": args.forward_hours,
        "example_sync_command": (
            f"PYTHONPATH=src python3 -m pb_wave_agent_hub.cli.sync_binance_history "
            f"--snapshot {snapshot_paths[0]} --start {start_dt.isoformat()} --end {end_dt.isoformat()}"
        ),
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
